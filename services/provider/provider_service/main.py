"""AuthBridge provider service: the EHR simulator backend.

Builds standards payloads and talks to the payer exactly as an EHR would:
CDS Hooks order-select / order-sign (CRD), $questionnaire-package (DTR),
Claim/$submit (PAS), and a rest-hook endpoint for PAS Subscription
notifications."""

import logging
import os
import threading
import time

import httpx
from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from authbridge_common import fhir as F
from authbridge_common.config import load_settings
from authbridge_common.letters import appeal_draft

from . import builders as B
from .autofill import autofill

log = logging.getLogger("provider")
FHIR_JSON = "application/fhir+json"
STATUS_BY_ACTION = {"A1": "APPROVED", "A6": "APPROVED", "A3": "DENIED", "A4": "PENDED"}


def create_app(settings=None, store=None, payer_client=None, register_subscription=True):
    settings = settings or load_settings("provider")
    if store is None:
        if settings.use_snowflake:
            from .store import SnowflakeProviderStore
            store = SnowflakeProviderStore(settings)
        else:
            from .store import MockProviderStore
            store = MockProviderStore(settings)
    sql = getattr(store, "sql", None)
    payer_base = os.getenv("PAYER_BASE_URL", "http://localhost:8002").rstrip("/")
    self_base = os.getenv("PROVIDER_CALLBACK_URL", "http://localhost:8001").rstrip("/")
    payer = payer_client or httpx.Client(base_url=payer_base, timeout=60)

    app = FastAPI(title="AuthBridge provider service (EHR simulator)", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.state.store = store

    # ------------------------------------------------------------ helpers
    def ctx_resources(order):
        p = store.get_patient(order["patient_id"])
        pr = store.practitioners[order["practitioner_role_id"]]
        role, practitioner = B.practitioner_resources(pr, store.org)
        return B.patient_resource(p), B.coverage_resource(p), role, practitioner, store.org, p, pr

    def call_payer(order, endpoint, path, payload, ok=(200, 201)):
        started = time.time()
        r = payer.post(path, json=payload, headers={"Content-Type": FHIR_JSON})
        try:
            body = r.json()
        except ValueError:
            body = {"text": r.text}
        order.setdefault("exchanges", []).append({
            "at": F.now_iso(), "endpoint": endpoint, "status": r.status_code,
            "ms": int((time.time() - started) * 1000), "request": payload, "response": body})
        if r.status_code not in ok:
            msg = body.get("issue", [{}])[0].get("diagnostics") if isinstance(body, dict) else None
            raise HTTPException(502, "Payer returned %s for %s: %s" % (r.status_code, endpoint, msg or r.text[:300]))
        return body

    def event(order, label, detail=None):
        order.setdefault("timeline", []).append({"at": F.now_iso(), "label": label, "detail": detail})

    def load(order_id):
        o = store.get_order(order_id)
        if not o:
            raise HTTPException(404, "Unknown order")
        return o

    def visible_notes(order):
        attached = set((order.get("dtr") or {}).get("attached_doc_ids", []))
        return [n for n in store.patient_notes(order["patient_id"]) if not n.get("attach_on_request") or n["doc_id"] in attached]

    # ------------------------------------------------------------ reference data
    @app.get("/health")
    def health():
        return {"status": "ok", "backend": settings.backend, "ai": settings.ai, "payer": payer_base}

    @app.get("/api/context")
    def context():
        return {"organization": store.org, "practitioners": list(store.practitioners.values()),
                "catalog": list(store.catalog.values()), "diagnoses": store.diagnoses,
                "backend": settings.backend, "ai": settings.ai}

    @app.get("/api/patients")
    def patients():
        out = []
        for p in store.list_patients():
            orders = store.list_orders(p["patient_id"])
            latest = sorted(orders, key=lambda o: o["updated_at"])[-1] if orders else None
            out.append(dict(p, latest_order=_summary(latest) if latest else None))
        return out

    @app.get("/api/patients/{patient_id}")
    def patient(patient_id: str):
        p = store.get_patient(patient_id)
        if not p:
            raise HTTPException(404, "Unknown patient")
        notes = store.patient_notes(patient_id)
        return dict(p, notes=[n for n in notes if not n.get("attach_on_request")],
                    pending_documents=[{k: n[k] for k in ("doc_id", "title", "note_type", "encounter_date")} for n in notes if n.get("attach_on_request")],
                    orders=[_summary(o) for o in sorted(store.list_orders(patient_id), key=lambda o: o["updated_at"], reverse=True)])

    # ------------------------------------------------------------ orders + CRD
    @app.post("/api/orders")
    def create_order(body: dict = Body(...)):
        """Save a draft order and fire order-select (CRD secondary hook)."""
        item = store.catalog.get(body.get("code"))
        if not item or not store.get_patient(body.get("patient_id")):
            raise HTTPException(400, "Choose a patient and an orderable service")
        if body.get("practitioner_role_id") not in store.practitioners:
            raise HTTPException(400, "Choose an ordering practitioner")
        order_id = F.new_id("ord").replace("ord-", "")
        form = {k: body.get(k) for k in ("reason_code", "reason_display", "frequency", "route", "duration_value",
                                         "duration_unit", "quantity", "priority", "note", "dosage_text")}
        order = {"order_id": order_id, "patient_id": body["patient_id"], "practitioner_role_id": body["practitioner_role_id"],
                 "code": item["code"], "display": item["display"], "resource_type": item["resource_type"], "form": form,
                 "status": "DRAFT", "created_at": F.now_iso(), "updated_at": F.now_iso()}
        order["resource"] = B.order_resource(order_id, body["patient_id"], body["practitioner_role_id"], item, form)
        patient_r, coverage, role, practitioner, org, _, _ = ctx_resources(order)
        req = B.hook_request("order-select", patient_r, coverage, role, practitioner, org, order["resource"])
        resp = call_payer(order, "order-select", "/cds-services/order-select-crd", req)
        order["select_result"] = resp
        event(order, "Order saved", "order-select returned %d card(s)" % len(resp.get("cards", [])))
        store.save_order(order)
        return order

    @app.post("/api/orders/{order_id}/sign")
    def sign_order(order_id: str):
        """Fire order-sign (CRD primary hook) and apply the coverage-information systemAction."""
        order = load(order_id)
        patient_r, coverage, role, practitioner, org, _, _ = ctx_resources(order)
        req = B.hook_request("order-sign", patient_r, coverage, role, practitioner, org, order["resource"])
        resp = call_payer(order, "order-sign", "/cds-services/order-sign-crd", req)
        info = None
        for action in resp.get("systemActions", []):
            res = action.get("resource", {})
            if action.get("type") == "update" and res.get("id") == order["resource"]["id"]:
                order["resource"] = res  # accept the payer's annotated order
                info = F.parse_coverage_information(res)
        order["crd"] = {"coverage_information": info, "cards": resp.get("cards", [])}
        order["status"] = _status_from_crd(info)
        event(order, "Order signed", _crd_sentence(info))
        order["updated_at"] = F.now_iso()
        store.save_order(order)
        return order

    # ------------------------------------------------------------ DTR
    @app.post("/api/orders/{order_id}/dtr")
    def start_dtr(order_id: str):
        """$questionnaire-package, pre-population, then AI auto-fill with evidence."""
        order = load(order_id)
        info = (order.get("crd") or {}).get("coverage_information") or {}
        if info.get("doc_needed") not in ("clinical", "admin", "both", "conditional"):
            raise HTTPException(409, "The payer did not ask for documentation on this order")
        patient_r, coverage, *_ = ctx_resources(order)
        params = B.package_request(coverage, order["resource"], info.get("questionnaire_url"), info.get("coverage_assertion_id"))
        pkg = call_payer(order, "$questionnaire-package", "/fhir/Questionnaire/$questionnaire-package", params)
        bundle = next(p["resource"] for p in pkg["parameter"] if p["name"] == "packagebundle")
        questionnaire = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Questionnaire")
        prefilled = B.prepopulate(questionnaire, {"patient": patient_r, "coverage": coverage, "orderCode": order["code"]})
        dtr = dict(order.get("dtr") or {}, questionnaire=questionnaire, prefilled=prefilled,
                   attached_doc_ids=(order.get("dtr") or {}).get("attached_doc_ids", []))
        order["dtr"] = dtr
        _run_autofill(order)
        order["status"] = "IN_DTR" if order["status"] in ("DOC_NEEDED", "IN_DTR") else order["status"]
        event(order, "Documentation started", "%d of %d answers filled from the chart" % (
            len(dtr["answers"]), len(B.criteria_link_ids(questionnaire))))
        order["updated_at"] = F.now_iso()
        store.save_order(order)
        return order

    def _run_autofill(order):
        dtr = order["dtr"]
        items = B.criteria_items(dtr["questionnaire"])
        notes = visible_notes(order)
        answers, rejected = autofill(settings, sql, order["patient_id"], items, notes)
        kept = {k: v for k, v in (dtr.get("answers") or {}).items() if v.get("origin") in ("override", "manual")}
        answers.update(kept)
        dtr["answers"] = answers
        dtr["rejected_ai_answers"] = rejected
        dtr["completeness"] = _completeness(order)

    def _completeness(order):
        dtr = order["dtr"]
        body = {"questionnaire_id": dtr["questionnaire"]["id"], "answers": dtr.get("answers", {}),
                "documents": [{"doc_id": n["doc_id"], "text": n["text"]} for n in visible_notes(order)]}
        r = payer.post("/internal/completeness", json=body)
        return r.json() if r.status_code == 200 else None

    @app.put("/api/orders/{order_id}/answers")
    def update_answers(order_id: str, body: dict = Body(...)):
        """Clinician edits. Changed AI answers become origin=override; new ones manual."""
        order = load(order_id)
        answers = order["dtr"].setdefault("answers", {})
        for link_id, value in (body.get("answers") or {}).items():
            current = answers.get(link_id)
            if value in (None, ""):
                answers.pop(link_id, None)
            elif current and _same(current.get("value"), value):
                continue
            elif current and current.get("origin") == "auto":
                # The AI quote supported the old value, not this one, so the evidence is dropped.
                answers[link_id] = {"value": value, "origin": "override", "replaced_ai_value": current.get("value")}
            else:
                answers[link_id] = dict(current or {}, value=value, origin=(current or {}).get("origin") or "manual")
        order["dtr"]["completeness"] = _completeness(order)
        order["updated_at"] = F.now_iso()
        store.save_order(order)
        return order

    @app.post("/api/orders/{order_id}/attach")
    def attach_document(order_id: str, body: dict = Body(...)):
        """Attach a chart document (e.g. PT notes requested on a pend) and refresh AI answers."""
        order = load(order_id)
        doc_id = body.get("doc_id")
        if doc_id not in {n["doc_id"] for n in store.patient_notes(order["patient_id"])}:
            raise HTTPException(400, "Unknown document")
        dtr = order.setdefault("dtr", {})
        dtr.setdefault("attached_doc_ids", [])
        if doc_id not in dtr["attached_doc_ids"]:
            dtr["attached_doc_ids"].append(doc_id)
        if dtr.get("questionnaire"):
            _run_autofill(order)
        event(order, "Document attached", doc_id)
        order["updated_at"] = F.now_iso()
        store.save_order(order)
        return order

    # ------------------------------------------------------------ PAS
    @app.post("/api/orders/{order_id}/submit")
    def submit(order_id: str):
        order = load(order_id)
        dtr = order.get("dtr") or {}
        if not dtr.get("questionnaire"):
            raise HTTPException(409, "Complete the documentation first")
        patient_r, coverage, role, practitioner, org, _, _ = ctx_resources(order)
        qr = B.questionnaire_response(F.new_id("qr"), dtr["questionnaire"], dtr.get("answers", {}), dtr.get("prefilled", {}),
                                      order["patient_id"], order["resource"])
        cited = {a.get("doc_id") for a in dtr.get("answers", {}).values() if a.get("doc_id")}
        cited |= set(dtr.get("attached_doc_ids", []))
        notes = [n for n in visible_notes(order) if n["doc_id"] in cited]
        prior = (order.get("pas") or {}).get("claim_id")
        bundle = B.pas_bundle(order_id, patient_r, coverage, role, practitioner, org, order["resource"], qr, notes,
                              store.catalog[order["code"]], order["form"], update_of=prior)
        resp = call_payer(order, "Claim/$submit", "/fhir/Claim/$submit", bundle)
        _apply_claim_response(order, resp, "Submitted to payer" if not prior else "Resubmitted with new documents")
        store.save_order(order)
        return order

    def _apply_claim_response(order, bundle, label):
        cr = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "ClaimResponse")
        item = F.first(cr.get("item")) or {}
        adj = F.first(item.get("adjudication")) or {}
        review = F.find_extension(adj, F.PAS_REVIEW_ACTION) or {}
        subs = review.get("extension", [])
        code = (F.first((F.ext_value(subs, "code") or {}).get("coding")) or {}).get("code")
        period = F.ext_value(item.get("extension", []), F.PAS_ITEM_PREAUTH_PERIOD) or {}
        pas = order.setdefault("pas", {})
        pas.update({
            "claim_id": cr["request"]["reference"].split("/")[-1],
            "pa_id": (F.first(cr.get("identifier")) or {}).get("value"),
            "review_action": code,
            "review_action_display": F.REVIEW_ACTION_DISPLAY.get(code),
            "auth_number": F.ext_value(subs, "number") or cr.get("preAuthRef"),
            "admin_ref": F.ext_value(item.get("extension", []), F.PAS_ADMIN_REF),
            "period": period,
            "reason_text": cr.get("disposition"),
            "request_text": (F.first(cr.get("processNote")) or {}).get("text"),
            "updated_at": F.now_iso(),
        })
        pas.setdefault("history", []).append({"at": F.now_iso(), "review_action": code, "reason_text": cr.get("disposition")})
        order["status"] = STATUS_BY_ACTION.get(code, "SUBMITTED")
        event(order, label, "%s %s" % (code, F.REVIEW_ACTION_DISPLAY.get(code, "")))
        order["updated_at"] = F.now_iso()

    @app.post("/notifications")
    def notifications(bundle: dict = Body(...)):
        """PAS Subscription rest-hook: the payer pushes decisions on pended requests."""
        inner = next((e["resource"] for e in bundle.get("entry", []) if e.get("resource", {}).get("resourceType") == "Bundle"), None)
        if not inner:
            return {"status": "ignored"}
        cr = next(e["resource"] for e in inner["entry"] if e["resource"]["resourceType"] == "ClaimResponse")
        order = store.find_order_by_claim(cr["request"]["reference"].split("/")[-1])
        if not order:
            return {"status": "unknown-claim"}
        order.setdefault("exchanges", []).append({"at": F.now_iso(), "endpoint": "notification", "status": 200,
                                                  "request": bundle, "response": {}})
        _apply_claim_response(order, inner, "Payer update received")
        store.save_order(order)
        return {"status": "ok"}

    @app.post("/api/orders/{order_id}/appeal-draft")
    def draft_appeal(order_id: str):
        order = load(order_id)
        pa_id = (order.get("pas") or {}).get("pa_id")
        if not pa_id:
            raise HTTPException(409, "No payer decision to appeal")
        r = payer.get("/internal/cases/%s" % pa_id)
        if r.status_code != 200:
            raise HTTPException(502, "Could not load the payer decision")
        case = r.json()
        pr = store.practitioners[order["practitioner_role_id"]]
        order["appeal_draft"] = appeal_draft(case, pr["name"])
        event(order, "Appeal drafted")
        store.save_order(order)
        return order

    @app.get("/api/orders/{order_id}")
    def get_order(order_id: str):
        return load(order_id)

    @app.get("/api/orders/{order_id}/documents")
    def order_documents(order_id: str):
        """Chart documents usable for this order, plus scanned ones that can be attached."""
        order = load(order_id)
        visible = visible_notes(order)
        ids = {n["doc_id"] for n in visible}
        attachable = [{k: n[k] for k in ("doc_id", "title", "note_type", "encounter_date")}
                      for n in store.patient_notes(order["patient_id"]) if n["doc_id"] not in ids]
        return {"documents": visible, "attachable": attachable}

    @app.get("/api/orders")
    def list_orders():
        return [_summary(o) for o in sorted(store.list_orders(), key=lambda o: o["updated_at"], reverse=True)]

    def register():
        sub = B.subscription(self_base + "/notifications", F.npi_of(store.org))
        for attempt in range(30):
            try:
                r = payer.post("/fhir/Subscription", json=sub)
                if r.status_code in (200, 201):
                    log.info("Registered PAS subscription with payer")
                    return True
            except httpx.HTTPError:
                pass
            time.sleep(min(2 + attempt, 10))
        log.warning("Could not register PAS subscription; pended updates will need a refresh")
        return False

    app.state.register_subscription = register
    if register_subscription:
        threading.Thread(target=register, daemon=True).start()
    return app


def _same(a, b):
    try:
        return float(a) == float(b) and not isinstance(a, bool) and not isinstance(b, bool)
    except (TypeError, ValueError):
        return str(a).lower() == str(b).lower()


def _status_from_crd(info):
    if not info:
        return "SIGNED"
    if info.get("covered") == "not-covered":
        return "NOT_COVERED"
    pa = info.get("pa_needed")
    if pa == "no-auth":
        return "NO_AUTH_NEEDED"
    if pa == "satisfied":
        return "GOLD_CARD"
    if info.get("doc_needed") in ("clinical", "admin", "both"):
        return "DOC_NEEDED"
    if pa == "auth-needed":
        return "DOC_NEEDED"
    return "SIGNED"


def _crd_sentence(info):
    if not info:
        return "No coverage information returned"
    if info.get("covered") == "not-covered":
        return "Not covered: %s" % (info.get("reason_text") or "")
    pa = info.get("pa_needed")
    if pa == "no-auth":
        return "Covered, no prior authorization needed"
    if pa == "satisfied":
        return "Covered, prior authorization satisfied (%s)" % info.get("satisfied_pa_id")
    return "Covered, prior authorization needed with %s documentation" % (info.get("doc_needed") or "no")


def _summary(o):
    return {k: o.get(k) for k in ("order_id", "patient_id", "code", "display", "status", "created_at", "updated_at")} | {
        "review_action": (o.get("pas") or {}).get("review_action"),
        "auth_number": (o.get("pas") or {}).get("auth_number") or ((o.get("crd") or {}).get("coverage_information") or {}).get("satisfied_pa_id"),
    }


app = None
if os.getenv("AUTHBRIDGE_NO_AUTOAPP") != "1":
    app = create_app()
