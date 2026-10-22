"""Builds the FHIR and CDS Hooks payloads an EHR sends: patient context,
draft orders, CDS Hooks requests, DTR QuestionnaireResponse and the PAS
request Bundle."""

import base64
import uuid

from authbridge_common import fhir as F

PAYER_ORG_ID = "org-demo-health-plan"
UCUM = "http://unitsofmeasure.org"

FREQUENCIES = {
    "once": None,
    "daily": {"frequency": 1, "period": 1, "periodUnit": "d"},
    "twice-daily": {"frequency": 2, "period": 1, "periodUnit": "d"},
    "weekly": {"frequency": 1, "period": 1, "periodUnit": "wk"},
    "nightly": {"frequency": 1, "period": 1, "periodUnit": "d", "when": ["HS"]},
    "continuous": {"frequency": 1, "period": 1, "periodUnit": "d"},
}
ROUTES = {
    "subcutaneous": ("34206005", "Subcutaneous route"),
    "oral": ("26643006", "Oral route"),
    "intravenous": ("47625008", "Intravenous route"),
    "intramuscular": ("78421000", "Intramuscular route"),
    "inhalation": ("447694001", "Respiratory tract route"),
}
DURATION_UNITS = {"d": "days", "wk": "weeks", "mo": "months"}


def patient_resource(p):
    return {
        "resourceType": "Patient", "id": p["patient_id"],
        "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]},
        "identifier": [{"system": "https://lakeside.example/mrn", "value": p["mrn"]}],
        "name": [{"family": p["family"], "given": [p["given"]]}],
        "gender": p["gender"], "birthDate": p["birth_date"],
        "address": [{"city": p.get("city"), "state": p.get("state"), "country": "US"}],
    }


def coverage_resource(p):
    c = p["coverage"]
    return {
        "resourceType": "Coverage", "id": c["coverage_id"], "status": "active",
        "subscriberId": c["member_id"],
        "beneficiary": {"reference": "Patient/%s" % p["patient_id"]},
        "payor": [{"reference": "Organization/%s" % PAYER_ORG_ID}],
        "class": [{"type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/coverage-class", "code": "plan"}]},
                   "value": c["plan_id"]}],
        "period": {"start": c["period_start"], "end": c["period_end"]},
    }


def practitioner_resources(pr, org):
    practitioner = {
        "resourceType": "Practitioner", "id": pr["practitioner_id"],
        "identifier": [{"system": F.NPI_SYSTEM, "value": pr["npi"]}],
        "name": [{"family": pr["family"], "given": [pr["given"]], "prefix": ["Dr."]}],
    }
    role = {
        "resourceType": "PractitionerRole", "id": pr["practitioner_role_id"],
        "practitioner": {"reference": "Practitioner/%s" % pr["practitioner_id"]},
        "organization": {"reference": "Organization/%s" % org["id"]},
        "specialty": [{"text": pr["specialty"]}],
    }
    return role, practitioner


def payer_org():
    return {"resourceType": "Organization", "id": PAYER_ORG_ID, "name": "Demo Health Plan"}


def order_resource(order_id, patient_id, practitioner_role_id, item, form):
    """item: catalog row; form: composer fields (reason, frequency, route, duration, quantity, priority)."""
    code = {"coding": [F.coding(item["code_system"], item["code"], item["display"])], "text": item["display"]}
    reason = [{"coding": [F.coding("ICD10", form["reason_code"], form.get("reason_display"))]}] if form.get("reason_code") else []
    timing = {}
    freq = FREQUENCIES.get(form.get("frequency") or "once")
    if freq:
        timing["repeat"] = dict(freq)
    if form.get("duration_value"):
        unit = form.get("duration_unit") or "mo"
        bounds = {"value": float(form["duration_value"]), "unit": DURATION_UNITS.get(unit, unit), "system": UCUM, "code": unit}
        timing.setdefault("repeat", {})["boundsDuration"] = bounds
    common = {
        "status": "draft", "subject": {"reference": "Patient/%s" % patient_id},
        "encounter": {"reference": "Encounter/enc-%s" % patient_id},
        "requester": {"reference": "PractitionerRole/%s" % practitioner_role_id},
        "reasonCode": reason, "authoredOn": F.now_iso(),
        "priority": "urgent" if form.get("priority") == "expedited" else "routine",
    }
    if form.get("note"):
        common["note"] = [{"text": form["note"]}]
    if item["resource_type"] == "MedicationRequest":
        dosage = {"text": form.get("dosage_text") or item["display"]}
        if timing:
            dosage["timing"] = timing
        if form.get("route") in ROUTES:
            rc, rd = ROUTES[form["route"]]
            dosage["route"] = {"coding": [{"system": "http://snomed.info/sct", "code": rc, "display": rd}], "text": rd}
        res = dict(common, resourceType="MedicationRequest", id="mr-%s" % order_id, intent="order",
                   medicationCodeableConcept=code, dosageInstruction=[dosage])
        if timing.get("repeat", {}).get("boundsDuration"):
            res["dispenseRequest"] = {"expectedSupplyDuration": timing["repeat"]["boundsDuration"],
                                      "quantity": {"value": float(form.get("quantity") or 1)}}
        return res
    res = dict(common, resourceType="ServiceRequest", id="sr-%s" % order_id, intent="original-order",
               meta={"profile": [F.PROFILES["crd_service_request"]]}, code=code,
               quantityQuantity={"value": float(form.get("quantity") or 1)})
    if timing:
        res["occurrenceTiming"] = timing
    return res


def hook_request(hook, patient, coverage, role, practitioner, org, order):
    ref = "%s/%s" % (order["resourceType"], order["id"])
    ctx = {
        "userId": "PractitionerRole/%s" % role["id"],
        "patientId": patient["id"],
        "encounterId": "enc-%s" % patient["id"],
        "draftOrders": {"resourceType": "Bundle", "type": "collection", "entry": [{"resource": order}]},
    }
    if hook == "order-select":
        ctx["selections"] = [ref]
    return {
        "hook": hook,
        "hookInstance": str(uuid.uuid4()),
        "context": ctx,
        "prefetch": {
            "patient": patient,
            "coverage": {"resourceType": "Bundle", "type": "searchset", "entry": [{"resource": coverage}]},
            "practitionerRole": {"resourceType": "Bundle", "type": "searchset",
                                 "entry": [{"resource": role}, {"resource": practitioner}, {"resource": org}]},
        },
    }


def package_request(coverage, order, questionnaire_url, assertion_id):
    params = [{"name": "coverage", "resource": coverage}, {"name": "order", "resource": order}]
    if questionnaire_url:
        params.append({"name": "questionnaire", "valueCanonical": questionnaire_url})
    if assertion_id:
        params.append({"name": "context", "valueString": assertion_id})
    return {"resourceType": "Parameters", "parameter": params}


def prepopulate(questionnaire, ctx):
    values = {}
    for item in F.iter_items(questionnaire.get("item")):
        ext = F.find_extension(item, F.SDC_INITIAL_EXPR)
        if ext:
            v = F.eval_fhirpath(ext["valueExpression"]["expression"], ctx)
            if v is not None:
                values[item["linkId"]] = v
    return values


def criteria_items(questionnaire):
    return [{"linkId": i["linkId"], "text": i.get("text"), "type": i.get("type")}
            for i in F.iter_items(questionnaire.get("item"))
            if i.get("type") not in ("group", "display") and not i.get("readOnly")]


def criteria_link_ids(questionnaire):
    return [i["linkId"] for i in F.iter_items(questionnaire.get("item"))
            if i.get("type") not in ("group", "display") and not i.get("readOnly")]


def _evidence_ext(ans):
    sub = []
    if ans.get("quote"):
        sub.append({"url": "quote", "valueString": ans["quote"]})
    if ans.get("doc_id"):
        sub.append({"url": "source", "valueReference": {"reference": "DocumentReference/%s" % ans["doc_id"]}})
    if ans.get("confidence"):
        sub.append({"url": "confidence", "valueString": ans["confidence"]})
    return {"url": F.AB_EVIDENCE, "extension": sub} if sub else None


def questionnaire_response(qr_id, questionnaire, answers, prefilled, patient_id, order):
    def build(items):
        out = []
        for it in items or []:
            node = {"linkId": it["linkId"], "text": it.get("text")}
            if it.get("type") == "group":
                node["item"] = build(it.get("item"))
                out.append(node)
                continue
            if it.get("type") == "display":
                continue
            ans = answers.get(it["linkId"]) or {}
            value = ans.get("value") if ans else prefilled.get(it["linkId"])
            av = F.answer_value(it.get("type"), value)
            if av is None:
                continue
            ev = _evidence_ext(ans)
            if ev:
                av["extension"] = [ev]
            origin = ans.get("origin") or ("auto" if it["linkId"] in prefilled else "manual")
            node["extension"] = [{"url": F.DTR_INFO_ORIGIN, "extension": [{"url": "source", "valueCode": origin}]}]
            node["answer"] = [av]
            out.append(node)
        return out

    return {
        "resourceType": "QuestionnaireResponse", "id": qr_id,
        "meta": {"profile": [F.PROFILES["dtr_qr"]]},
        "questionnaire": "%s|%s" % (questionnaire["url"], questionnaire["version"]),
        "status": "completed", "subject": {"reference": "Patient/%s" % patient_id}, "authored": F.now_iso(),
        "extension": [{"url": F.DTR_QR_CONTEXT, "valueReference": {"reference": "%s/%s" % (order["resourceType"], order["id"])}}],
        "item": build(questionnaire.get("item")),
    }


def document_reference(note, patient_id):
    return {
        "resourceType": "DocumentReference", "id": note["doc_id"], "status": "current",
        "type": {"text": note["note_type"]}, "subject": {"reference": "Patient/%s" % patient_id},
        "date": note["encounter_date"] + "T00:00:00Z", "description": note.get("title"),
        "content": [{"attachment": {"contentType": "text/plain", "title": note.get("title"),
                                    "data": base64.b64encode(note["text"].encode()).decode()}}],
    }


def pas_bundle(order_id, patient, coverage, role, practitioner, org, order, qr, notes, item, form, update_of=None):
    claim_id = "claim-%s" % order_id
    supporting = [{"sequence": 1, "category": {"coding": [{"system": F.PAS_TEMP_CS, "code": "additionalInformation"}]},
                   "valueReference": {"reference": "QuestionnaireResponse/%s" % qr["id"]}}]
    for i, n in enumerate(notes, start=2):
        supporting.append({"sequence": i, "category": {"coding": [{"system": F.PAS_TEMP_CS, "code": "additionalInformation"}]},
                           "valueReference": {"reference": "DocumentReference/%s" % n["doc_id"]}})
    claim = {
        "resourceType": "Claim", "id": claim_id, "meta": {"profile": [F.PROFILES["pas_claim"]]},
        "identifier": [{"system": "https://lakeside.example/claims", "value": claim_id}],
        "status": "active",
        "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/claim-type", "code": "professional"}]},
        "use": "preauthorization",
        "patient": {"reference": "Patient/%s" % patient["id"]},
        "created": F.now_iso(),
        "insurer": {"reference": "Organization/%s" % PAYER_ORG_ID},
        "provider": {"reference": "PractitionerRole/%s" % role["id"]},
        "priority": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/processpriority",
                                 "code": "stat" if form.get("priority") == "expedited" else "normal"}]},
        "insurance": [{"sequence": 1, "focal": True, "coverage": {"reference": "Coverage/%s" % coverage["id"]}}],
        "diagnosis": [{"sequence": 1, "diagnosisCodeableConcept": {"coding": [F.coding("ICD10", form.get("reason_code"))]}}] if form.get("reason_code") else [],
        "supportingInfo": supporting,
        "item": [{
            "sequence": 1, "diagnosisSequence": [1] if form.get("reason_code") else [],
            "productOrService": {"coding": [F.coding(item["code_system"], item["code"], item["display"])]},
            "quantity": {"value": float(form.get("quantity") or 1)},
            "extension": [{"url": F.PAS_REQUESTED_SERVICE, "valueReference": {"reference": "%s/%s" % (order["resourceType"], order["id"])}}],
        }],
    }
    if update_of:
        claim["related"] = [{"claim": {"identifier": {"system": "https://lakeside.example/claims", "value": update_of}},
                             "relationship": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/related-claim-relationship", "code": "prior"}]}}]
    entries = [claim, patient, coverage, payer_org(), role, practitioner, org, order, qr] + [document_reference(n, patient["id"]) for n in notes]
    return {
        "resourceType": "Bundle", "id": F.new_id("pasreq"),
        "meta": {"profile": [F.PROFILES["pas_request_bundle"]]},
        "identifier": {"system": "https://lakeside.example/pas", "value": F.new_id("req")},
        "type": "collection", "timestamp": F.now_iso(),
        "entry": [{"fullUrl": "urn:uuid:%s-%s" % (r["resourceType"].lower(), r["id"]), "resource": r} for r in entries],
    }


def subscription(endpoint, org_npi):
    return {
        "resourceType": "Subscription", "status": "requested", "reason": "PAS decision updates for Lakeside Family Medicine",
        "criteria": F.PAS_SUBSCRIPTION_TOPIC,
        "_criteria": {"extension": [{"url": F.BACKPORT_FILTER, "valueString": "Claim?org-identifier=%s" % org_npi}]},
        "channel": {"type": "rest-hook", "endpoint": endpoint, "payload": "application/fhir+json",
                    "_payload": {"extension": [{"url": F.BACKPORT_PAYLOAD, "valueCode": "full-resource"}]}},
    }
