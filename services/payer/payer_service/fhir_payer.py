"""Payer-side FHIR translation: parse inbound CRD/DTR/PAS payloads into plain
records for the repository, and build standard responses from its results.
This layer holds no business rules; decisions come from the repository
(Snowflake stored procedures or the mock)."""

import base64
import copy

from authbridge_common import fhir as F


def index_bundle(bundle):
    out = {}
    for e in bundle.get("entry", []) or []:
        r = e.get("resource") or {}
        if r.get("resourceType") and r.get("id"):
            out["%s/%s" % (r["resourceType"], r["id"])] = r
    return out


def bundle_resources(bundle, resource_type=None):
    return [e["resource"] for e in (bundle or {}).get("entry", []) or []
            if "resource" in e and (resource_type is None or e["resource"].get("resourceType") == resource_type)]


# ---- CRD ---------------------------------------------------------------------
def hook_inputs(body):
    ctx = body.get("context", {})
    prefetch = body.get("prefetch") or {}
    coverages = [r for r in bundle_resources(prefetch.get("coverage"), "Coverage") if r.get("status") == "active"]
    coverage = coverages[0] if coverages else None
    member_id = None
    if coverage:
        member_id = coverage.get("subscriberId") or (F.first(coverage.get("identifier")) or {}).get("value")
    npi = None
    for r in bundle_resources(prefetch.get("practitionerRole")):
        npi = npi or F.npi_of(r)
    orders = bundle_resources(ctx.get("draftOrders"))
    if body.get("hook") == "order-select" and ctx.get("selections"):
        wanted = set(ctx["selections"])
        orders = [o for o in orders if "%s/%s" % (o["resourceType"], o["id"]) in wanted]
    return {"patient_id": ctx.get("patientId"), "coverage": coverage, "member_id": member_id,
            "ordering_npi": npi, "orders": orders}


def system_action_for(order, info, coverage):
    updated = copy.deepcopy(order)
    updated["extension"] = [e for e in updated.get("extension", []) if e.get("url") != F.CRD_COVERAGE_INFO]
    updated["extension"].append(F.build_coverage_information(info, "Coverage/%s" % coverage["id"]))
    return {"type": "update", "description": "Coverage information from Demo Health Plan", "resource": updated}


def guideline_card(info, payer_base):
    policy = info.get("policy_doc_id")
    if not policy or info.get("pa_needed") != "auth-needed":
        return None
    return {
        "uuid": F.new_id("card"),
        "summary": "Review the plan's coverage policy for this order",
        "indicator": "info",
        "detail": "Documentation requirements are listed in policy %s." % policy,
        "source": {"label": "Demo Health Plan", "topic": {"code": "guideline", "system": F.CRD_TEMP_CS}},
        "links": [{"label": "Open policy %s" % policy, "url": "%s/policies/%s" % (payer_base, policy), "type": "absolute"}],
    }


# ---- DTR -----------------------------------------------------------------------
def package_inputs(params):
    out = {"coverage": None, "orders": [], "questionnaires": [], "context": None}
    for p in params.get("parameter", []) or []:
        name = p.get("name")
        if name == "coverage":
            out["coverage"] = p.get("resource")
        elif name == "order":
            out["orders"].append(p.get("resource"))
        elif name == "questionnaire":
            out["questionnaires"].append(p.get("valueCanonical"))
        elif name == "context":
            out["context"] = p.get("valueString")
    return out


def questionnaire_package(questionnaire, coverage, order, context):
    canonical = "%s|%s" % (questionnaire["url"], questionnaire["version"])
    qr = {
        "resourceType": "QuestionnaireResponse",
        "id": F.new_id("qr"),
        "meta": {"profile": [F.PROFILES["dtr_qr"]]},
        "questionnaire": canonical,
        "status": "in-progress",
        "subject": (coverage or {}).get("beneficiary"),
        "authored": F.now_iso(),
        "extension": [{"url": F.DTR_QR_CONTEXT, "valueReference": {"reference": "%s/%s" % (order["resourceType"], order["id"])}}] if order else [],
    }
    bundle = {"resourceType": "Bundle", "id": F.new_id("pkg"), "type": "collection", "timestamp": F.now_iso(),
              "entry": [{"resource": questionnaire}, {"resource": qr}]}
    params = {"resourceType": "Parameters", "parameter": [{"name": "packagebundle", "resource": bundle}]}
    if context:
        params["parameter"].append({"name": "context", "valueString": context})
    return params


# ---- PAS -----------------------------------------------------------------------
def _decode_attachment(att):
    if att.get("data"):
        try:
            return base64.b64decode(att["data"]).decode("utf-8")
        except Exception:  # noqa: BLE001
            return ""
    return ""


def parse_qr(qr):
    answers = {}
    for item in F.iter_items(qr.get("item")):
        ans = F.first(item.get("answer"))
        if not ans:
            continue
        value = F.read_answer(ans)
        evidence = F.find_extension(ans, F.AB_EVIDENCE) or F.find_extension(item, F.AB_EVIDENCE)
        origin_ext = F.find_extension(item, F.DTR_INFO_ORIGIN)
        sub = (evidence or {}).get("extension", [])
        answers[item["linkId"]] = {
            "value": value,
            "quote": F.ext_value(sub, "quote"),
            "doc_id": (F.ext_value(sub, "source") or {}).get("reference", "").split("/")[-1] or None,
            "confidence": F.ext_value(sub, "confidence"),
            "origin": F.ext_value((origin_ext or {}).get("extension", []), "source") or "manual",
        }
    return answers


def parse_pas_bundle(bundle):
    idx = index_bundle(bundle)
    claim = bundle["entry"][0]["resource"]
    patient_ref = claim["patient"]["reference"]
    coverage = idx.get(F.first(claim.get("insurance", []))["coverage"]["reference"]) or {}
    role = idx.get(claim.get("provider", {}).get("reference")) or {}
    practitioner = idx.get((role.get("practitioner") or {}).get("reference")) or {}
    org = idx.get((role.get("organization") or {}).get("reference")) or {}
    item = F.first(claim.get("item")) or {}
    system, code, display = F.order_code({"code": item.get("productOrService", {})})
    order = None
    for e in item.get("extension", []):
        if e.get("url") == F.PAS_REQUESTED_SERVICE:
            order = idx.get(e["valueReference"]["reference"])
    assertion = None
    if order:
        info = F.parse_coverage_information(order) or {}
        assertion = info.get("coverage_assertion_id")
    priority_code = (F.first((claim.get("priority") or {}).get("coding")) or {}).get("code")
    answers, documents, questionnaire_id = {}, [], None
    for si in claim.get("supportingInfo", []):
        ref = (si.get("valueReference") or {}).get("reference")
        res = idx.get(ref)
        if not res:
            continue
        if res["resourceType"] == "QuestionnaireResponse":
            answers.update(parse_qr(res))
            questionnaire_id = res.get("questionnaire", "").split("|")[0].rstrip("/").split("/")[-1]
        elif res["resourceType"] == "DocumentReference":
            content = F.first(res.get("content")) or {}
            att = content.get("attachment", {})
            documents.append({"doc_id": res["id"], "title": att.get("title") or res.get("description"),
                              "encounter_date": (res.get("date") or "")[:10], "text": _decode_attachment(att)})
    related = F.first(claim.get("related"))
    return {
        "claim_id": claim["id"],
        "claim_identifier": (F.first(claim.get("identifier")) or {}).get("value"),
        "is_update": bool(related),
        "patient_id": patient_ref.split("/")[-1],
        "member_id": coverage.get("subscriberId"),
        "ordering_npi": F.npi_of(practitioner),
        "provider_org_npi": F.npi_of(org),
        "service_code": code, "code_system": system, "service_display": display,
        "icd10": [F.first(d.get("diagnosisCodeableConcept", {}).get("coding", [{}])).get("code") for d in claim.get("diagnosis", [])],
        "priority": "expedited" if priority_code in ("stat", "urgent") else "standard",
        "coverage_assertion_id": assertion,
        "questionnaire_id": questionnaire_id,
        "answers": answers,
        "documents": documents,
    }


def claim_response_bundle(result, claim_id, patient_id, payer):
    action = result["review_action"]
    item_ext = []
    if result.get("period_start"):
        item_ext.append({"url": F.PAS_ITEM_PREAUTH_PERIOD, "valuePeriod": {"start": result["period_start"], "end": result["period_end"]}})
    if result.get("admin_ref"):
        item_ext.append({"url": F.PAS_ADMIN_REF, "valueString": result["admin_ref"]})
    review = [{"url": "code", "valueCodeableConcept": {"coding": [{"system": F.X12_306, "code": action, "display": F.REVIEW_ACTION_DISPLAY.get(action)}]}}]
    if result.get("auth_number"):
        review.insert(0, {"url": "number", "valueString": result["auth_number"]})
    if action in ("A3", "A4") and result.get("reason_text"):
        review.append({"url": "reasonCode", "valueCodeableConcept": {"text": result["reason_text"]}})
    notes = []
    if result.get("request_text"):
        notes.append({"number": 1, "type": "display", "text": result["request_text"]})
    cr = {
        "resourceType": "ClaimResponse",
        "id": F.new_id("cr"),
        "meta": {"profile": [F.PROFILES["pas_claimresponse"]]},
        "identifier": [{"system": "https://authbridge.example/payer/pa", "value": result["pa_id"]}],
        "status": "active",
        "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/claim-type", "code": "professional"}]},
        "use": "preauthorization",
        "patient": {"reference": "Patient/%s" % patient_id},
        "created": F.now_iso(),
        "insurer": {"reference": "Organization/%s" % payer["organization_id"]},
        "request": {"reference": "Claim/%s" % claim_id},
        "outcome": "queued" if action == "A4" else "complete",
        "disposition": result.get("reason_text"),
        "item": [{
            "itemSequence": 1,
            "extension": item_ext,
            "adjudication": [{
                "category": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/adjudication", "code": "submitted"}]},
                "extension": [{"url": F.PAS_REVIEW_ACTION, "extension": review}],
            }],
        }],
    }
    if result.get("auth_number"):
        cr["preAuthRef"] = result["auth_number"]
    if notes:
        cr["processNote"] = notes
    return {
        "resourceType": "Bundle",
        "id": F.new_id("pasresp"),
        "meta": {"profile": [F.PROFILES["pas_response_bundle"]]},
        "identifier": {"system": "https://authbridge.example/payer/response", "value": F.new_id("r")},
        "type": "collection",
        "timestamp": F.now_iso(),
        "entry": [
            {"fullUrl": "urn:uuid:%s" % cr["id"], "resource": cr},
            {"resource": {"resourceType": "Patient", "id": patient_id}},
            {"resource": {"resourceType": "Organization", "id": payer["organization_id"], "name": payer["name"]}},
        ],
    }


def notification_bundle(subscription_id, response_bundle):
    return {
        "resourceType": "Bundle",
        "id": F.new_id("notif"),
        "type": "history",
        "timestamp": F.now_iso(),
        "entry": [
            {"resource": {"resourceType": "Parameters", "parameter": [
                {"name": "subscription", "valueReference": {"reference": "Subscription/%s" % subscription_id}},
                {"name": "topic", "valueCanonical": F.PAS_SUBSCRIPTION_TOPIC},
                {"name": "status", "valueCode": "active"},
                {"name": "type", "valueCode": "event-notification"},
            ]}},
            {"fullUrl": "urn:uuid:%s" % response_bundle["id"], "resource": response_bundle},
        ],
    }
