"""AuthBridge payer service: CDS Hooks (CRD), DTR and PAS endpoints, plus the
internal API behind the payer workbench. Runs locally; all data, rules and AI
live in Snowflake when AUTHBRIDGE_BACKEND=snowflake."""

import logging
import os
import threading

import httpx
from fastapi import BackgroundTasks, Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

from authbridge_common import fhir as F
from authbridge_common.config import load_settings
from authbridge_common.letters import denial_letter
from authbridge_common.validation import (outcome, run_validator_cli, validate_hook_request,
                                          validate_pas_bundle)

from . import agents
from . import fhir_payer as P

log = logging.getLogger("payer")
FHIR_JSON = "application/fhir+json"


def create_app(settings=None, repo=None, notify_client=None):
    settings = settings or load_settings("payer")
    if repo is None:
        if settings.use_snowflake:
            from .repo_snowflake import SnowflakePayerRepo
            repo = SnowflakePayerRepo(settings)
        else:
            from .repo_mock import MockPayerRepo
            repo = MockPayerRepo(settings)
    cortex = None
    if settings.use_cortex:
        from authbridge_common.snowflake_client import CortexAgents
        cortex = CortexAgents(settings)

    public_base = os.getenv("PAYER_PUBLIC_URL", "http://localhost:8002")
    app = FastAPI(title="AuthBridge payer service", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.state.repo = repo
    app.state.settings = settings
    notifier = notify_client or httpx.Client(timeout=10)

    def fhir(content, status=200):
        return JSONResponse(content, status_code=status, media_type=FHIR_JSON)

    def validate_async(direction, endpoint, correlation, payload):
        """Optional deep validation with the HL7 validator jar, off the request path."""
        if settings.validator_mode != "cli":
            return
        def work():
            res = run_validator_cli(payload, settings.validator_jar)
            repo.log_exchange(direction, endpoint + "#validator", correlation, payload, res)
        threading.Thread(target=work, daemon=True).start()

    # ---------------------------------------------------------------- health
    @app.get("/health")
    def health():
        return {"status": "ok", "backend": settings.backend, "ai": settings.ai}

    # ---------------------------------------------------------------- CRD
    @app.get("/cds-services")
    def discovery():
        prefetch = {
            "patient": "Patient/{{context.patientId}}",
            "coverage": "Coverage?patient={{context.patientId}}&status=active",
            "practitionerRole": "PractitionerRole?_id={{userPractitionerRoleId}}&_include=PractitionerRole:practitioner&_include=PractitionerRole:organization",
        }
        ext = {"davinci-crd.configuration": [], "davinci-crd.version": ["2.2"]}
        return {"services": [
            {"id": "order-select-crd", "hook": "order-select", "title": "Demo Health Plan coverage requirements (order-select)",
             "description": "Early coverage information while an order is drafted.", "prefetch": prefetch, "extension": ext},
            {"id": "order-sign-crd", "hook": "order-sign", "title": "Demo Health Plan coverage requirements (order-sign)",
             "description": "Coverage, prior authorization and documentation requirements at signing.", "prefetch": prefetch, "extension": ext},
        ]}

    def handle_hook(body, hook):
        issues, status = validate_hook_request(body, hook)
        correlation = body.get("hookInstance")
        repo.log_exchange("IN", hook, correlation, body, outcome(issues))
        if status != 200:
            return fhir(outcome(issues), status)
        inputs = P.hook_inputs(body)
        cards, actions = [], []
        if inputs["coverage"] and inputs["member_id"]:
            for order in inputs["orders"]:
                system, code, _ = F.order_code(order)
                info = repo.crd_evaluate(inputs["member_id"], inputs["patient_id"], code, system, inputs["ordering_npi"], hook)
                actions.append(P.system_action_for(order, info, inputs["coverage"]))
                if hook == "order-sign":
                    card = P.guideline_card(info, public_base)
                    if card:
                        cards.append(card)
        response = {"cards": cards, "systemActions": actions}
        repo.log_exchange("OUT", hook, correlation, response)
        validate_async("IN", hook, correlation, body)
        return response

    @app.post("/cds-services/order-select-crd")
    def order_select(body: dict = Body(...)):
        return handle_hook(body, "order-select")

    @app.post("/cds-services/order-sign-crd")
    def order_sign(body: dict = Body(...)):
        return handle_hook(body, "order-sign")

    @app.post("/cds-services/{service_id}/feedback")
    def hook_feedback(service_id: str, body: dict = Body(...)):
        repo.log_exchange("IN", "feedback", service_id, body)
        return {}

    @app.get("/policies/{policy_id}", response_class=PlainTextResponse)
    def policy(policy_id: str):
        sections = repo.policy_sections(policy_id)
        if not sections:
            raise HTTPException(404, "Unknown policy")
        return "\n\n".join("%s\n%s" % (s["section_title"], s["text"]) for s in sections)

    # ---------------------------------------------------------------- DTR
    @app.post("/fhir/Questionnaire/$questionnaire-package")
    def questionnaire_package(params: dict = Body(...)):
        inputs = P.package_inputs(params)
        repo.log_exchange("IN", "$questionnaire-package", inputs["context"], params)
        if not inputs["coverage"] or not inputs["orders"]:
            return fhir(outcome([("error", "required", "coverage and order are required")]), 400)
        qid = None
        if inputs["questionnaires"]:
            qid = inputs["questionnaires"][0].split("|")[0].rstrip("/").split("/")[-1]
        else:
            info = F.parse_coverage_information(inputs["orders"][0]) or {}
            if info.get("questionnaire_url"):
                qid = info["questionnaire_url"].split("|")[0].split("/")[-1]
        questionnaire = repo.get_questionnaire(qid) if qid else None
        if not questionnaire:
            return fhir(outcome([("error", "not-found", "No questionnaire for this order")]), 404)
        result = P.questionnaire_package(questionnaire, inputs["coverage"], inputs["orders"][0], inputs["context"])
        repo.log_exchange("OUT", "$questionnaire-package", inputs["context"], result)
        return fhir(result)

    # ---------------------------------------------------------------- PAS
    @app.post("/fhir/Claim/$submit")
    def claim_submit(bundle: dict = Body(...)):
        issues = validate_pas_bundle(bundle)
        correlation = (bundle.get("identifier") or {}).get("value")
        repo.log_exchange("IN", "Claim/$submit", correlation, bundle, outcome(issues))
        if any(i[0] == "error" for i in issues):
            return fhir(outcome(issues), 400)
        req = P.parse_pas_bundle(bundle)
        if req["is_update"]:
            req["related_pa_id"] = repo.find_pa_by_claim(req["claim_id"])
        result = repo.pas_submit(req)
        if result.get("error"):
            return fhir(outcome([("error", "business-rule", result["message"])]), 422)
        response = P.claim_response_bundle(result, req["claim_id"], req["patient_id"], repo.payer)
        repo.log_exchange("OUT", "Claim/$submit", correlation, response)
        validate_async("IN", "Claim/$submit", correlation, bundle)
        return fhir(response)

    @app.post("/fhir/Subscription")
    def subscribe(sub: dict = Body(...)):
        channel = sub.get("channel") or {}
        if channel.get("type") != "rest-hook" or not channel.get("endpoint"):
            return fhir(outcome([("error", "invalid", "rest-hook channel with an endpoint is required")]), 400)
        org = None
        for e in (sub.get("_criteria") or {}).get("extension", []):
            if e.get("url") == F.BACKPORT_FILTER and "org-identifier=" in e.get("valueString", ""):
                org = e["valueString"].split("org-identifier=")[-1]
        sub = dict(sub, id=sub.get("id") or F.new_id("sub"), status="active")
        repo.add_subscription(sub["id"], org, channel["endpoint"], sub)
        return fhir(sub, 201)

    def notify(result):
        response = P.claim_response_bundle(result, result["claim_id"], result["patient_id"], repo.payer)
        for s in repo.list_subscriptions(result.get("provider_org_npi")):
            bundle = P.notification_bundle(s["subscription_id"], response)
            try:
                notifier.post(s["endpoint"], json=bundle, headers={"Content-Type": FHIR_JSON})
                repo.log_exchange("OUT", "notification", result["pa_id"], bundle)
            except httpx.HTTPError as exc:
                log.warning("notification to %s failed: %s", s["endpoint"], exc)

    # ---------------------------------------------------------------- internal (payer UI)
    @app.get("/internal/queue")
    def work_queue():
        return repo.queue()

    @app.get("/internal/cases/{pa_id}")
    def get_case(pa_id: str):
        case = repo.case(pa_id)
        if not case:
            raise HTTPException(404, "Unknown request")
        return case

    @app.post("/internal/cases/{pa_id}/decision")
    def decide(pa_id: str, background: BackgroundTasks, body: dict = Body(...)):
        try:
            result = repo.record_decision(pa_id, body.get("action"), body.get("reviewer"), body.get("role"),
                                          body.get("reason_text"), body.get("request_text"))
        except PermissionError as exc:
            raise HTTPException(403, str(exc))
        except (ValueError, KeyError) as exc:
            raise HTTPException(400, str(exc))
        background.add_task(notify, result)
        return result

    @app.post("/internal/cases/{pa_id}/criteria/{node_id}/override")
    def override(pa_id: str, node_id: str, body: dict = Body(...)):
        try:
            return repo.override_criterion(pa_id, node_id, body.get("status"), body.get("reason"), body.get("reviewer"))
        except KeyError:
            raise HTTPException(404, "Unknown criterion")

    @app.get("/internal/cases/{pa_id}/letter", response_class=PlainTextResponse)
    def letter(pa_id: str):
        case = repo.case(pa_id)
        if not case:
            raise HTTPException(404, "Unknown request")
        return denial_letter(case)

    @app.post("/internal/completeness")
    def completeness(body: dict = Body(...)):
        """Provider-side pre-check (PRD FR-4.6): run the payer's criteria tree on draft answers."""
        docs = {d["doc_id"]: d for d in body.get("documents", [])}
        from authbridge_common.criteria import verify_quote
        facts = {k: dict(v, verified=verify_quote(v.get("quote"), (docs.get(v.get("doc_id")) or {}).get("text")))
                 for k, v in (body.get("answers") or {}).items()}
        result = repo.completeness(body.get("questionnaire_id"), facts)
        if result is None:
            raise HTTPException(404, "No policy for this questionnaire")
        return result

    @app.get("/internal/metrics")
    def metrics():
        return repo.metrics()

    @app.get("/internal/exchanges")
    def exchanges(correlation_id: str = None, limit: int = 50):
        return repo.list_exchanges(correlation_id, limit)

    @app.post("/internal/agents/{name}/run")
    def run_agent(name: str, body: dict = Body(...)):
        if name not in agents.AGENTS:
            raise HTTPException(404, "Unknown agent")
        if cortex:
            gen = agents.cortex_answer(name, body.get("message", ""), cortex, body.get("pa_id"),
                                       body.get("thread_id"), body.get("parent_message_id"))
        else:
            gen = agents.mock_answer(name, body.get("message", ""), repo, body.get("pa_id"))
        return StreamingResponse(gen, media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})

    return app


app = None
if os.getenv("AUTHBRIDGE_NO_AUTOAPP") != "1":
    app = create_app()
