"""FHIR validation for inbound payloads.

structural mode (default): fast checks of the shapes CRD and PAS depend on.
cli mode: additionally runs the HL7 FHIR Validator jar against the Da Vinci
and US Core packages. The jar is slow to start, so it is run on demand and its
OperationOutcome is stored with the raw payload, not used to block a request.
"""

import json
import os
import subprocess
import tempfile

from .fhir import operation_outcome

REQUIRED = {
    "Patient": ["name", "gender", "birthDate"],
    "Coverage": ["status", "beneficiary", "payor"],
    "ServiceRequest": ["status", "intent", "code", "subject"],
    "MedicationRequest": ["status", "intent", "subject"],
    "DeviceRequest": ["status", "intent", "subject"],
    "Claim": ["status", "type", "use", "patient", "created", "insurer", "provider", "priority", "insurance", "item"],
    "QuestionnaireResponse": ["questionnaire", "status"],
    "PractitionerRole": [],
    "Practitioner": [],
    "Organization": ["name"],
    "DocumentReference": ["status", "content"],
}

IG_PACKAGES = [
    "hl7.fhir.us.core#6.1.0",
    "hl7.fhir.us.davinci-crd#2.2.1",
    "hl7.fhir.us.davinci-dtr#2.2.0",
    "hl7.fhir.us.davinci-pas#2.2.1",
]


def check_resource(res, where):
    issues = []
    rt = res.get("resourceType")
    if not rt:
        return [("error", "structure", "%s: missing resourceType" % where)]
    for field in REQUIRED.get(rt, []):
        if res.get(field) in (None, [], {}, ""):
            issues.append(("error", "required", "%s %s: missing %s" % (where, rt, field)))
    return issues


def validate_hook_request(body, hook):
    """CDS Hooks request checks (CRD 2.2). Returns (issues, http_status)."""
    issues = []
    for field in ("hook", "hookInstance", "context"):
        if field not in body:
            issues.append(("error", "required", "missing %s" % field))
    if issues:
        return issues, 400
    if body["hook"] != hook:
        issues.append(("error", "invalid", "hook is %s, expected %s" % (body["hook"], hook)))
    ctx = body.get("context") or {}
    for field in ("userId", "patientId", "draftOrders"):
        if field not in ctx:
            issues.append(("error", "required", "context.%s missing" % field))
    draft = ctx.get("draftOrders") or {}
    if draft.get("resourceType") != "Bundle" or draft.get("type") != "collection":
        issues.append(("error", "invalid", "context.draftOrders must be a Bundle of type collection"))
    for i, e in enumerate(draft.get("entry", []) or []):
        issues += check_resource(e.get("resource", {}), "draftOrders.entry[%d]" % i)
    if hook == "order-sign":
        cov = (body.get("prefetch") or {}).get("coverage")
        entries = [e.get("resource", {}) for e in (cov or {}).get("entry", [])] if cov else []
        active = [r for r in entries if r.get("resourceType") == "Coverage" and r.get("status") == "active"]
        if len(active) != 1:
            issues.append(("error", "business-rule", "prefetch.coverage must contain exactly one active Coverage (found %d)" % len(active)))
            return issues, 400
    errors = [i for i in issues if i[0] == "error"]
    return issues, (400 if errors else 200)


def validate_pas_bundle(bundle):
    issues = []
    if bundle.get("resourceType") != "Bundle" or bundle.get("type") != "collection":
        return [("error", "invalid", "PAS request must be a Bundle of type collection")]
    entries = bundle.get("entry") or []
    if not entries or entries[0].get("resource", {}).get("resourceType") != "Claim":
        return [("error", "invalid", "the first entry must be the Claim")]
    claim = entries[0]["resource"]
    if claim.get("use") != "preauthorization":
        issues.append(("error", "invalid", "Claim.use must be preauthorization"))
    present = {"%s/%s" % (e["resource"].get("resourceType"), e["resource"].get("id")) for e in entries if "resource" in e}
    for i, e in enumerate(entries):
        issues += check_resource(e.get("resource", {}), "entry[%d]" % i)
    for ref in _references(claim):
        if "/" in ref and not ref.startswith("http") and ref not in present:
            issues.append(("error", "not-found", "Claim references %s, which is not in the Bundle" % ref))
    return issues


def _references(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "reference" and isinstance(v, str):
                yield v
            else:
                yield from _references(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _references(v)


def outcome(issues):
    return operation_outcome(issues or [("information", "informational", "No structural issues found")])


def run_validator_cli(resource, jar_path, timeout=180):
    """Run the HL7 validator on one resource. Returns an OperationOutcome dict.
    Example: java -jar validator_cli.jar file.json -version 4.0.1 -ig <pkg> -output out.json
    Check the validator's --help for your version; flags change occasionally."""
    if not jar_path or not os.path.exists(jar_path):
        return operation_outcome([("warning", "not-supported", "FHIR validator jar not configured")])
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "resource.json")
        out = os.path.join(d, "out.json")
        with open(src, "w") as f:
            json.dump(resource, f)
        cmd = ["java", "-jar", jar_path, src, "-version", "4.0.1", "-output", out]
        for pkg in IG_PACKAGES:
            cmd += ["-ig", pkg]
        try:
            subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
            with open(out) as f:
                return json.load(f)
        except Exception as exc:  # noqa: BLE001 - surface any validator failure as an outcome
            return operation_outcome([("warning", "exception", "Validator did not run: %s" % exc)])
