"""End-to-end tests in mock mode: the provider service talks to the payer
service over HTTP (in-process), exactly as in Docker Compose.

Run from services/:  pytest -q
"""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for sub in ("common", "payer", "provider"):
    sys.path.insert(0, str(ROOT / sub))
os.environ["AUTHBRIDGE_NO_AUTOAPP"] = "1"
os.environ["AUTHBRIDGE_BACKEND"] = "mock"
os.environ["AUTHBRIDGE_AI"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402

from authbridge_common import criteria as engine  # noqa: E402
from payer_service.main import create_app as create_payer  # noqa: E402
from provider_service.main import create_app as create_provider  # noqa: E402


class _LateClient:
    """Lets the payer notify a provider app that is created after it."""
    target = None

    def post(self, url, **kw):
        return self.target.post(url.replace("http://localhost:8001", ""), **kw)


@pytest.fixture()
def system():
    late = _LateClient()
    payer_app = create_payer(notify_client=late)
    payer = TestClient(payer_app)
    provider_app = create_provider(payer_client=payer, register_subscription=False)
    provider = TestClient(provider_app)
    late.target = provider
    assert provider_app.state.register_subscription()
    return payer, provider


def order(provider, patient, code, reason, practitioner="pr-patel", **extra):
    body = {"patient_id": patient, "code": code, "reason_code": reason, "practitioner_role_id": practitioner,
            "frequency": "once", "quantity": 1, "priority": "standard"}
    body.update(extra)
    r = provider.post("/api/orders", json=body)
    assert r.status_code == 200, r.text
    o = r.json()
    r = provider.post("/api/orders/%s/sign" % o["order_id"])
    assert r.status_code == 200, r.text
    return r.json()


def document_and_submit(provider, o):
    r = provider.post("/api/orders/%s/dtr" % o["order_id"])
    assert r.status_code == 200, r.text
    r = provider.post("/api/orders/%s/submit" % o["order_id"])
    assert r.status_code == 200, r.text
    return r.json()


def test_discovery(system):
    payer, _ = system
    services = payer.get("/cds-services").json()["services"]
    assert {s["hook"] for s in services} == {"order-select", "order-sign"}


def test_no_auth_short_circuit(system):
    _, provider = system
    o = order(provider, "pt-002", "72100", "M54.50")
    assert o["status"] == "NO_AUTH_NEEDED"
    assert o["crd"]["coverage_information"]["pa_needed"] == "no-auth"


def test_gold_card(system):
    _, provider = system
    o = order(provider, "pt-002", "72148", "M54.16", practitioner="pr-rao")
    info = o["crd"]["coverage_information"]
    assert o["status"] == "GOLD_CARD"
    assert info["pa_needed"] == "satisfied" and info["satisfied_pa_id"].startswith("GC-72148")
    assert info["reason_code"] == "gold-card"


def test_cpap_auto_approves_with_verified_evidence(system):
    _, provider = system
    o = order(provider, "pt-001", "E0601", "G47.33", frequency="nightly", duration_value=3, duration_unit="mo")
    assert o["status"] == "DOC_NEEDED"
    assert o["crd"]["coverage_information"]["questionnaire_url"].endswith("q-pap-initial|1.0.0")
    o = provider.post("/api/orders/%s/dtr" % o["order_id"]).json()
    answers = o["dtr"]["answers"]
    assert answers["ahi"]["value"] == 22 and "AHI" in answers["ahi"]["quote"]
    assert answers["f2f_before_sleep_test"]["value"] is True
    assert o["dtr"]["completeness"]["recommendation"] == engine.AUTO_APPROVE
    o = provider.post("/api/orders/%s/submit" % o["order_id"]).json()
    assert o["status"] == "APPROVED" and o["pas"]["review_action"] == "A1"
    assert o["pas"]["auth_number"]


def test_lumbar_mri_pends_then_approves_after_pt_notes(system):
    payer, provider = system
    o = order(provider, "pt-002", "72148", "M54.16")
    o = document_and_submit(provider, o)
    assert o["status"] == "PENDED" and o["pas"]["review_action"] == "A4"
    assert "conservative care" in o["pas"]["request_text"]
    o = provider.post("/api/orders/%s/attach" % o["order_id"], json={"doc_id": "doc-002-3"}).json()
    assert o["dtr"]["answers"]["conservative_weeks"]["value"] == 6
    o = provider.post("/api/orders/%s/submit" % o["order_id"]).json()
    assert o["status"] == "APPROVED"
    # same payer request, now version 2
    case = payer.get("/internal/cases/%s" % o["pas"]["pa_id"]).json()
    assert case["request"]["version"] == 2


def test_red_flag_mri_auto_approves(system):
    _, provider = system
    o = order(provider, "pt-003", "72148", "G83.4", priority="expedited")
    o = document_and_submit(provider, o)
    assert o["status"] == "APPROVED"


def test_oxygen_goes_to_clinician_and_only_medical_director_can_deny(system):
    payer, provider = system
    o = order(provider, "pt-004", "E1390", "J44.9", frequency="continuous", duration_value=12, duration_unit="mo")
    o = document_and_submit(provider, o)
    assert o["status"] == "PENDED"  # provider sees A4 while a clinician reviews
    pa_id = o["pas"]["pa_id"]
    queue = payer.get("/internal/queue").json()
    row = next(r for r in queue if r["pa_id"] == pa_id)
    assert row["status"] == "CLINICIAN_REVIEW" and row["recommendation"] == engine.RECOMMEND_DENY
    r = payer.post("/internal/cases/%s/decision" % pa_id, json={"action": "DENY", "reviewer": "nurse.jordan", "role": "UM_NURSE", "reason_text": "x"})
    assert r.status_code == 403
    r = payer.post("/internal/cases/%s/decision" % pa_id, json={
        "action": "DENY", "reviewer": "dr.chen", "role": "MEDICAL_DIRECTOR",
        "reason_text": "No qualifying SpO2 at rest, exercise or sleep (O2-2)."})
    assert r.status_code == 200 and r.json()["review_action"] == "A3"
    o = provider.get("/api/orders/%s" % o["order_id"]).json()  # updated by Subscription notification
    assert o["status"] == "DENIED"
    o = provider.post("/api/orders/%s/appeal-draft" % o["order_id"]).json()
    assert "reconsideration" in o["appeal_draft"]
    letter = payer.get("/internal/cases/%s/letter" % pa_id).text
    assert "NOT CERTIFIED" in letter and "licensed clinician" in letter


def test_glp1_medication_order(system):
    payer, provider = system
    o = order(provider, "pt-005", "SEMAGLUTIDE-2.4", "E66.01", frequency="weekly", route="subcutaneous",
              duration_value=3, duration_unit="mo")
    assert o["resource"]["resourceType"] == "MedicationRequest"
    assert o["resource"]["dosageInstruction"][0]["route"]["coding"][0]["code"] == "34206005"
    o = document_and_submit(provider, o)
    case = payer.get("/internal/cases/%s" % o["pas"]["pa_id"]).json()
    assert case["request"]["recommendation"] == engine.RECOMMEND_DENY


def test_override_drops_ai_evidence_and_pends(system):
    _, provider = system
    o = order(provider, "pt-001", "E0601", "G47.33")
    o = provider.post("/api/orders/%s/dtr" % o["order_id"]).json()
    o = provider.put("/api/orders/%s/answers" % o["order_id"], json={"answers": {"ahi": 30}}).json()
    assert o["dtr"]["answers"]["ahi"]["origin"] == "override" and "quote" not in o["dtr"]["answers"]["ahi"]
    o = provider.post("/api/orders/%s/submit" % o["order_id"]).json()
    assert o["status"] == "PENDED"


def test_bad_hook_request_is_rejected(system):
    payer, _ = system
    r = payer.post("/cds-services/order-sign-crd", json={"hook": "order-sign", "hookInstance": "x", "context": {
        "userId": "PractitionerRole/pr-patel", "patientId": "pt-001",
        "draftOrders": {"resourceType": "Bundle", "type": "collection", "entry": []}}, "prefetch": {}})
    assert r.status_code == 400 and r.json()["resourceType"] == "OperationOutcome"


def test_metrics_and_mock_agent(system):
    payer, _ = system
    m = payer.get("/internal/metrics").json()
    assert m["total_requests"] >= 80 and 0 < m["sla_compliance"] <= 1
    r = payer.post("/internal/agents/analytics/run", json={"message": "How are we doing?"})
    assert r.status_code == 200 and '"type": "done"' in r.text


def test_criteria_engine_three_valued_logic():
    nodes = [
        {"node_id": "r", "parent_node_id": None, "node_type": "OR", "label": "root", "policy_section_id": "S", "sort_order": 1},
        {"node_id": "a", "parent_node_id": "r", "node_type": "LEAF", "label": "A", "fact_name": "a", "operator": ">=", "threshold": 6,
         "on_not_met": "PEND", "policy_section_id": "S1", "sort_order": 2},
        {"node_id": "b", "parent_node_id": "r", "node_type": "LEAF", "label": "B", "fact_name": "b", "operator": "=", "threshold": True,
         "on_not_met": "PEND", "policy_section_id": "S2", "sort_order": 3},
    ]
    assert engine.evaluate(nodes, {})["recommendation"] == engine.PEND
    met = engine.evaluate(nodes, {"b": {"value": True, "quote": "x", "verified": True}})
    assert met["recommendation"] == engine.AUTO_APPROVE
    unverified = engine.evaluate(nodes, {"b": {"value": True, "quote": "x", "verified": False}})
    assert unverified["recommendation"] == engine.PEND
    assert engine.verify_quote("AHI of 22", "Index (AHI of 22  events)") is True
    assert engine.verify_quote("AHI of 23", "Index (AHI of 22 events)") is False
