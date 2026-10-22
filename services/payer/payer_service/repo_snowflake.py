"""Snowflake payer backend (AUTHBRIDGE_BACKEND=snowflake).

Business decisions are made by stored procedures (snowflake/sql/03, 04);
this class only calls them and reads tables/views for the workbench.
"""

import json

from authbridge_common.seed import load_seed, policy_sections
from authbridge_common.snowflake_client import SnowflakeSQL


class SnowflakePayerRepo:
    def __init__(self, settings):
        self.sql = SnowflakeSQL(settings)
        seed = load_seed(settings.seed_dir)
        self.payer = seed["payer"]["payer"]
        self._policies = seed["policies"]

    # ---- CRD -----------------------------------------------------------
    def crd_evaluate(self, member_id, patient_id, service_code, code_system, ordering_npi, hook):
        return self.sql.call("PAYER.SP_CRD_EVALUATE", member_id, patient_id, service_code, code_system, ordering_npi, hook)

    # ---- DTR -----------------------------------------------------------
    def get_questionnaire(self, questionnaire_id):
        rows = self.sql.query(
            "SELECT fhir FROM PAYER.QUESTIONNAIRE WHERE questionnaire_id = %s ORDER BY version DESC LIMIT 1", [questionnaire_id])
        return rows[0]["fhir"] if rows else None

    def completeness(self, questionnaire_id, facts):
        return self.sql.call("PAYER.SP_COMPLETENESS", questionnaire_id, json.dumps(facts))

    # ---- PAS -----------------------------------------------------------
    def find_pa_by_claim(self, claim_id):
        rows = self.sql.query("SELECT pa_id FROM PAYER.PA_REQUEST WHERE claim_id = %s", [claim_id])
        return rows[0]["pa_id"] if rows else None

    def pas_submit(self, req):
        return self.sql.call("PAYER.SP_PAS_SUBMIT", json.dumps(req))

    def record_decision(self, pa_id, action, reviewer, role, reason_text, request_text=None):
        try:
            return self.sql.call("PAYER.SP_RECORD_DECISION", pa_id, action, reviewer, role, reason_text, request_text)
        except Exception as exc:  # noqa: BLE001 - map SP errors to HTTP semantics
            msg = str(exc)
            if "Only a medical director" in msg:
                raise PermissionError("Only a medical director can issue a denial (A3).")
            if "Unknown request" in msg:
                raise KeyError(pa_id)
            raise ValueError(msg.splitlines()[-1][:300])

    def override_criterion(self, pa_id, node_id, status, reason, reviewer):
        n = self.sql.execute(
            "UPDATE AI.CLINICAL_REVIEW SET reviewer_override = %s, override_reason = %s, override_by = %s, "
            "override_at = CURRENT_TIMESTAMP() WHERE pa_id = %s AND node_id = %s "
            "AND version = (SELECT MAX(version) FROM AI.CLINICAL_REVIEW WHERE pa_id = %s)",
            [status, reason, reviewer, pa_id, node_id, pa_id])
        if not n:
            raise KeyError(node_id)
        return {"node_id": node_id, "reviewer_override": status, "override_reason": reason, "override_by": reviewer}

    # ---- workbench -----------------------------------------------------------
    def queue(self):
        return self.sql.query(
            "SELECT pa_id, member_id, patient_id, service_code, service_display, priority, status, recommendation, "
            "TO_VARCHAR(submitted_at) AS submitted_at, TO_VARCHAR(sla_due_at) AS sla_due_at, ordering_npi, line_of_business "
            "FROM PAYER.PA_REQUEST WHERE NOT is_historical ORDER BY sla_due_at")

    def case(self, pa_id):
        rows = self.sql.query("SELECT * FROM PAYER.PA_REQUEST WHERE pa_id = %s", [pa_id])
        if not rows:
            return None
        req = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in rows[0].items() if k != "criteria"}
        criteria = rows[0].get("criteria") or []
        overrides = {r["node_id"]: r for r in self.sql.query(
            "SELECT node_id, reviewer_override, override_reason, override_by FROM AI.CLINICAL_REVIEW "
            "WHERE pa_id = %s AND version = %s AND reviewer_override IS NOT NULL", [pa_id, req["version"]])}
        for c in criteria:
            if c["node_id"] in overrides:
                c.update({k: v for k, v in overrides[c["node_id"]].items() if k != "node_id"})
        ai_check = self.sql.query(
            "SELECT fact_name, provider_value, ai_value, quote, doc_id, citation_verified, agrees, model "
            "FROM AI.AI_REVIEW_RESULT WHERE pa_id = %s AND version = %s", [pa_id, req["version"]])
        qr = self.sql.query("SELECT answers FROM PAYER.QUESTIONNAIRE_RESPONSE WHERE pa_id = %s ORDER BY version DESC LIMIT 1", [pa_id])
        decisions = self.sql.query(
            "SELECT review_action_code, auth_number, admin_ref_number, TO_VARCHAR(auth_period_start) AS auth_period_start, "
            "TO_VARCHAR(auth_period_end) AS auth_period_end, reason_text, request_text, decided_by, decider_role, ai_assisted, "
            "TO_VARCHAR(decided_at) AS decided_at FROM PAYER.DECISION WHERE pa_id = %s ORDER BY decided_at", [pa_id])
        audit = self.sql.query(
            "SELECT agent_name, model, recommendation, human_actor, TO_VARCHAR(created_at) AS created_at, output "
            "FROM AI.AI_RECOMMENDATION_AUDIT WHERE pa_id = %s ORDER BY created_at", [pa_id])
        docs = self.sql.query(
            "SELECT doc_id, title, TO_VARCHAR(encounter_date) AS encounter_date, text FROM PAYER.SUBMITTED_DOCUMENT WHERE pa_id = %s", [pa_id])
        return {
            "request": req, "criteria": criteria, "answers": (qr[0]["answers"] if qr else {}) or {},
            "documents": docs, "decisions": decisions, "audit": audit, "ai_cross_check": ai_check,
            "policy_sections": self.policy_sections(req.get("policy_doc_id")),
            "decision": decisions[-1] if decisions else None,
        }

    def metrics(self):
        m = self.sql.query("SELECT * FROM ANALYTICS.V_PA_METRICS")[0]
        m = {k: (float(v) if v is not None and not isinstance(v, int) else v) for k, v in m.items()}
        m["by_service"] = self.sql.query("SELECT * FROM ANALYTICS.V_PA_BY_SERVICE")
        m["gold_card"] = self.sql.query("SELECT * FROM PAYER.GOLD_CARD_STATUS ORDER BY approval_rate DESC")
        return m

    # ---- exchanges and subscriptions ---------------------------------------------
    def log_exchange(self, direction, endpoint, correlation_id, payload, validation=None):
        status = None
        if validation:
            status = "error" if any(i.get("severity") == "error" for i in validation.get("issue", [])) else "ok"
        self.sql.execute(
            "INSERT INTO RAW.FHIR_RAW_BUNDLES (correlation_id, direction, endpoint, resource_type, payload, validation_status, validation_outcome) "
            "SELECT %s, %s, %s, %s, PARSE_JSON(%s), %s, PARSE_JSON(%s)",
            [correlation_id, direction, endpoint, (payload or {}).get("resourceType") or "CDSHooks",
             json.dumps(payload), status, json.dumps(validation)])

    def list_exchanges(self, correlation_id=None, limit=50):
        if correlation_id:
            return self.sql.query(
                "SELECT payload_id, direction, endpoint, correlation_id, payload, validation_outcome, TO_VARCHAR(received_at) AS received_at "
                "FROM RAW.FHIR_RAW_BUNDLES WHERE correlation_id = %%s ORDER BY received_at DESC LIMIT %d" % int(limit), [correlation_id])
        return self.sql.query(
            "SELECT payload_id, direction, endpoint, correlation_id, payload, validation_outcome, TO_VARCHAR(received_at) AS received_at "
            "FROM RAW.FHIR_RAW_BUNDLES ORDER BY received_at DESC LIMIT %d" % int(limit))

    def add_subscription(self, sub_id, org_identifier, endpoint, resource):
        self.sql.execute(
            "MERGE INTO PAYER.SUBSCRIPTION t USING (SELECT %s AS subscription_id, %s AS org_identifier, %s AS endpoint, "
            "PARSE_JSON(%s) AS fhir) s ON t.endpoint = s.endpoint "
            "WHEN MATCHED THEN UPDATE SET subscription_id = s.subscription_id, org_identifier = s.org_identifier, fhir = s.fhir, status = 'active' "
            "WHEN NOT MATCHED THEN INSERT (subscription_id, org_identifier, endpoint, status, fhir) "
            "VALUES (s.subscription_id, s.org_identifier, s.endpoint, 'active', s.fhir)",
            [sub_id, org_identifier, endpoint, json.dumps(resource)])

    def list_subscriptions(self, org_identifier=None):
        return self.sql.query(
            "SELECT subscription_id, org_identifier, endpoint FROM PAYER.SUBSCRIPTION WHERE status = 'active' "
            "AND (%s IS NULL OR org_identifier IS NULL OR org_identifier = %s)", [org_identifier, org_identifier])

    def policy_sections(self, policy_id):
        if policy_id in self._policies:
            return policy_sections(policy_id, self._policies[policy_id])
        rows = self.sql.query("SELECT section_id, section_title, chunk_text AS text FROM AI.POLICY_DOC_CHUNKS "
                              "WHERE policy_doc_id = %s ORDER BY chunk_id", [policy_id])
        return rows
