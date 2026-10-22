"""FHIR / CDS Hooks / Da Vinci constants and small helpers.

Extension URLs and code systems follow CRD 2.2.1, DTR 2.2.0 and PAS 2.2.1 as
summarized in docs/AuthBridge_PRD.md. Items marked VERIFY should be checked
against the published StructureDefinitions before claiming conformance.
"""

import re
import uuid
from datetime import datetime, timezone, date

# --- Code systems ----------------------------------------------------------
CODE_SYSTEMS = {
    "CPT": "http://www.ama-assn.org/go/cpt",
    "HCPCS": "https://bluebutton.cms.gov/resources/codesystem/hcpcs",
    "ICD10": "http://hl7.org/fhir/sid/icd-10-cm",
    # Demo-only code for the GLP-1 scenario. Replace with RxNorm/NDC before real use.
    "DEMO-DRUG": "https://authbridge.example/CodeSystem/demo-drug",
}
SYSTEM_TO_SHORT = {v: k for k, v in CODE_SYSTEMS.items()}
NPI_SYSTEM = "http://hl7.org/fhir/sid/us-npi"
X12_306 = "https://codesystem.x12.org/005010/306"

# --- Extensions --------------------------------------------------------------
CRD_COVERAGE_INFO = "http://hl7.org/fhir/us/davinci-crd/StructureDefinition/ext-coverage-information"
CRD_TEMP_CS = "http://hl7.org/fhir/us/davinci-crd/CodeSystem/temp"  # VERIFY reason code system
DTR_INFO_ORIGIN = "http://hl7.org/fhir/us/davinci-dtr/StructureDefinition/information-origin"  # VERIFY
DTR_QR_CONTEXT = "http://hl7.org/fhir/us/davinci-dtr/StructureDefinition/qr-context"
SDC_INITIAL_EXPR = "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-initialExpression"
AB_EVIDENCE = "https://authbridge.example/fhir/StructureDefinition/answer-evidence"
AB_POLICY_DOC = "https://authbridge.example/fhir/StructureDefinition/policy-doc-id"

PAS_REQUESTED_SERVICE = "http://hl7.org/fhir/us/davinci-pas/StructureDefinition/extension-requestedService"
PAS_REVIEW_ACTION = "http://hl7.org/fhir/us/davinci-pas/StructureDefinition/extension-reviewAction"
PAS_ITEM_PREAUTH_PERIOD = "http://hl7.org/fhir/us/davinci-pas/StructureDefinition/extension-itemPreAuthPeriod"
PAS_ADMIN_REF = "http://hl7.org/fhir/us/davinci-pas/StructureDefinition/extension-administrationReferenceNumber"  # VERIFY
PAS_TEMP_CS = "http://hl7.org/fhir/us/davinci-pas/CodeSystem/PASTempCodes"  # VERIFY
PAS_SUBSCRIPTION_TOPIC = "http://hl7.org/fhir/us/davinci-pas/SubscriptionTopic/PASSubscriptionTopic"  # VERIFY
BACKPORT_FILTER = "http://hl7.org/fhir/uv/subscriptions-backport/StructureDefinition/backport-filter-criteria"
BACKPORT_PAYLOAD = "http://hl7.org/fhir/uv/subscriptions-backport/StructureDefinition/backport-payload-content"

PROFILES = {
    "crd_service_request": "http://hl7.org/fhir/us/davinci-crd/StructureDefinition/profile-servicerequest",
    "dtr_qr": "http://hl7.org/fhir/us/davinci-dtr/StructureDefinition/dtr-questionnaireresponse",
    "pas_claim": "http://hl7.org/fhir/us/davinci-pas/StructureDefinition/profile-claim",
    "pas_request_bundle": "http://hl7.org/fhir/us/davinci-pas/StructureDefinition/profile-pas-request-bundle",
    "pas_response_bundle": "http://hl7.org/fhir/us/davinci-pas/StructureDefinition/profile-pas-response-bundle",
    "pas_claimresponse": "http://hl7.org/fhir/us/davinci-pas/StructureDefinition/profile-claimresponse",
}

REVIEW_ACTION_DISPLAY = {
    "A1": "Certified in total",
    "A3": "Not certified",
    "A4": "Pending",
    "A6": "Modified",
}


def new_id(prefix):
    return "%s-%s" % (prefix, uuid.uuid4().hex[:10])


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today():
    return date.today().isoformat()


def coding(system_short, code, display=None):
    c = {"system": CODE_SYSTEMS.get(system_short, system_short), "code": code}
    if display:
        c["display"] = display
    return c


def ext_value(extensions, url):
    """Return the value[x] of the first sub-extension with this url."""
    for e in extensions or []:
        if e.get("url") == url:
            for k, v in e.items():
                if k.startswith("value"):
                    return v
    return None


def find_extension(resource, url):
    for e in resource.get("extension", []) or []:
        if e.get("url") == url:
            return e
    return None


def order_code(resource):
    """(short_system, code, display) of a ServiceRequest/DeviceRequest/MedicationRequest."""
    cc = resource.get("code") or resource.get("codeCodeableConcept") or resource.get("medicationCodeableConcept") or {}
    for c in cc.get("coding", []):
        return SYSTEM_TO_SHORT.get(c.get("system"), c.get("system")), c.get("code"), c.get("display")
    return None, None, None


def first(lst):
    return lst[0] if isinstance(lst, list) and lst else None


def npi_of(resource):
    for ident in resource.get("identifier", []) or []:
        if ident.get("system") == NPI_SYSTEM:
            return ident.get("value")
    return None


def operation_outcome(issues):
    """issues: list of (severity, code, diagnostics)."""
    return {
        "resourceType": "OperationOutcome",
        "issue": [{"severity": s, "code": c, "diagnostics": d} for s, c, d in issues],
    }


# --- Coverage information (CRD) ---------------------------------------------
def build_coverage_information(info, coverage_ref):
    """Build ext-coverage-information from the payer's CRD evaluation result.

    info keys: covered, pa_needed, doc_needed, doc_purpose, questionnaire_url,
    coverage_assertion_id, satisfied_pa_id, reason_code, reason_text, date.
    Invariants: questionnaire implies doc-needed; not-covered implies no pa-needed;
    satisfied pa-needed if and only if satisfied-pa-id.
    """
    sub = [{"url": "coverage", "valueReference": {"reference": coverage_ref}},
           {"url": "covered", "valueCode": info["covered"]}]
    if info.get("covered") != "not-covered" and info.get("pa_needed"):
        sub.append({"url": "pa-needed", "valueCode": info["pa_needed"]})
    if info.get("doc_needed"):
        sub.append({"url": "doc-needed", "valueCode": info["doc_needed"]})
        if info.get("doc_purpose"):
            sub.append({"url": "doc-purpose", "valueCode": info["doc_purpose"]})
    if info.get("reason_code") or info.get("reason_text"):
        cc = {}
        if info.get("reason_code"):
            cc["coding"] = [{"system": CRD_TEMP_CS, "code": info["reason_code"]}]
        if info.get("reason_text"):
            cc["text"] = info["reason_text"]
        sub.append({"url": "reason", "valueCodeableConcept": cc})
    if info.get("pa_needed") == "satisfied" and info.get("satisfied_pa_id"):
        sub.append({"url": "satisfied-pa-id", "valueString": info["satisfied_pa_id"]})
    if info.get("questionnaire_url") and info.get("doc_needed"):
        sub.append({"url": "questionnaire", "valueCanonical": info["questionnaire_url"]})
    sub.append({"url": "date", "valueDate": info.get("date") or today()})
    sub.append({"url": "coverage-assertion-id", "valueString": info["coverage_assertion_id"]})
    return {"url": CRD_COVERAGE_INFO, "extension": sub}


def parse_coverage_information(resource):
    ext = find_extension(resource, CRD_COVERAGE_INFO)
    if not ext:
        return None
    subs = ext.get("extension", [])
    reason = ext_value(subs, "reason") or {}
    return {
        "covered": ext_value(subs, "covered"),
        "pa_needed": ext_value(subs, "pa-needed"),
        "doc_needed": ext_value(subs, "doc-needed"),
        "doc_purpose": ext_value(subs, "doc-purpose"),
        "questionnaire_url": ext_value(subs, "questionnaire"),
        "coverage_assertion_id": ext_value(subs, "coverage-assertion-id"),
        "satisfied_pa_id": ext_value(subs, "satisfied-pa-id"),
        "reason_code": (first(reason.get("coding")) or {}).get("code"),
        "reason_text": reason.get("text"),
        "date": ext_value(subs, "date"),
    }


# --- Minimal FHIRPath for questionnaire pre-population --------------------
def _split_concat(expr):
    parts, buf, quoted = [], "", False
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch == "'":
            quoted = not quoted
            buf += ch
        elif not quoted and expr[i:i + 3] == " + ":
            parts.append(buf)
            buf = ""
            i += 3
            continue
        else:
            buf += ch
        i += 1
    parts.append(buf)
    return [p.strip() for p in parts]


def _resolve(path, ctx):
    tokens = path.split(".")
    if not tokens[0].startswith("%"):
        return None
    cur = ctx.get(tokens[0][1:])
    for t in tokens[1:]:
        if t == "first()":
            cur = first(cur) if isinstance(cur, list) else cur
        else:
            if isinstance(cur, list):
                cur = first(cur)
            cur = cur.get(t) if isinstance(cur, dict) else None
        if cur is None:
            return None
    return first(cur) if isinstance(cur, list) else cur


def eval_fhirpath(expr, ctx):
    """Supports %var.path.first() chains and ' + ' concatenation with string
    literals. Enough for demographic pre-population; use a real FHIRPath/CQL
    engine for anything more."""
    parts = _split_concat(expr)
    if len(parts) == 1 and not parts[0].startswith("'"):
        return _resolve(parts[0], ctx)
    out = []
    for p in parts:
        if p.startswith("'") and p.endswith("'"):
            out.append(p[1:-1])
        else:
            v = _resolve(p, ctx)
            if v is None:
                return None
            out.append(str(v))
    return "".join(out)


def iter_items(items):
    for it in items or []:
        yield it
        for child in iter_items(it.get("item")):
            yield child


def answer_value(item_type, value):
    """Questionnaire item type -> QuestionnaireResponse answer element."""
    if value is None or value == "":
        return None
    if item_type == "boolean":
        if isinstance(value, str):
            value = value.lower() in ("true", "yes", "1")
        return {"valueBoolean": bool(value)}
    if item_type == "integer":
        return {"valueInteger": int(float(value))}
    if item_type == "decimal":
        return {"valueDecimal": float(value)}
    if item_type == "date":
        return {"valueDate": str(value)}
    return {"valueString": str(value)}


def read_answer(answer):
    for k, v in (answer or {}).items():
        if k.startswith("value"):
            if k == "valueCoding":
                return v.get("code")
            return v
    return None


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]
