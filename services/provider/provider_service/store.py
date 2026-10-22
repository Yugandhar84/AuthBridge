"""Provider-side (EHR) data: patients, notes and order workflow state.

Mock mode keeps everything in memory from shared/seed. Snowflake mode reads the
chart from CORE.* and keeps order state as VARIANT in PROVIDER.EHR_ORDER.
"""

import json
import threading

from authbridge_common.seed import load_seed


class MockProviderStore:
    def __init__(self, settings):
        seed = load_seed(settings.seed_dir)
        ehr = seed["ehr"]
        self.org = ehr["organization"]
        self.practitioners = {p["practitioner_role_id"]: p for p in ehr["practitioners"]}
        self.patients = {p["patient_id"]: p for p in ehr["patients"]}
        self.notes = ehr["notes"]
        self.catalog = {c["code"]: c for c in seed["payer"]["catalog"]}
        self.diagnoses = seed["payer"]["diagnoses"]
        self.orders = {}
        self.lock = threading.RLock()

    def list_patients(self):
        return list(self.patients.values())

    def get_patient(self, patient_id):
        return self.patients.get(patient_id)

    def patient_notes(self, patient_id):
        return [n for n in self.notes if n["patient_id"] == patient_id]

    def save_order(self, order):
        with self.lock:
            self.orders[order["order_id"]] = json.loads(json.dumps(order))

    def get_order(self, order_id):
        o = self.orders.get(order_id)
        return json.loads(json.dumps(o)) if o else None

    def list_orders(self, patient_id=None):
        return [o for o in self.orders.values() if not patient_id or o["patient_id"] == patient_id]

    def find_order_by_claim(self, claim_id):
        for o in self.orders.values():
            if (o.get("pas") or {}).get("claim_id") == claim_id:
                return self.get_order(o["order_id"])
        return None


class SnowflakeProviderStore(MockProviderStore):
    """Reference data still comes from the seed files (organization, catalog);
    patients, notes and orders come from Snowflake."""

    def __init__(self, settings):
        super().__init__(settings)
        from authbridge_common.snowflake_client import SnowflakeSQL
        self.sql = SnowflakeSQL(settings)

    def list_patients(self):
        rows = self.sql.query(
            "SELECT p.patient_id, p.mrn, p.given, p.family, TO_VARCHAR(p.birth_date) AS birth_date, p.gender, p.city, p.state,"
            " p.problems, p.demo_scenario AS scenario, p.suggested_order, p.suggested_reason,"
            " OBJECT_CONSTRUCT('coverage_id', c.coverage_id, 'member_id', c.member_id, 'plan_id', c.plan_id,"
            "   'period_start', TO_VARCHAR(c.period_start), 'period_end', TO_VARCHAR(c.period_end)) AS coverage"
            " FROM CORE.PATIENT p JOIN CORE.COVERAGE c ON c.patient_id = p.patient_id AND c.status = 'active'"
            " ORDER BY p.patient_id")
        return rows

    def get_patient(self, patient_id):
        return next((p for p in self.list_patients() if p["patient_id"] == patient_id), None)

    def patient_notes(self, patient_id):
        return self.sql.query(
            "SELECT doc_id, patient_id, note_type, TO_VARCHAR(encounter_date) AS encounter_date, author_npi, title, text,"
            " attach_on_request FROM CORE.CLINICAL_DOCUMENT WHERE patient_id = %s ORDER BY encounter_date", [patient_id])

    def save_order(self, order):
        self.sql.execute(
            "MERGE INTO PROVIDER.EHR_ORDER t USING (SELECT %s AS order_id, %s AS patient_id, %s AS status, PARSE_JSON(%s) AS data) s"
            " ON t.order_id = s.order_id"
            " WHEN MATCHED THEN UPDATE SET status = s.status, data = s.data, updated_at = CURRENT_TIMESTAMP()"
            " WHEN NOT MATCHED THEN INSERT (order_id, patient_id, status, data, updated_at)"
            " VALUES (s.order_id, s.patient_id, s.status, s.data, CURRENT_TIMESTAMP())",
            [order["order_id"], order["patient_id"], order["status"], json.dumps(order)])

    def get_order(self, order_id):
        rows = self.sql.query("SELECT data FROM PROVIDER.EHR_ORDER WHERE order_id = %s", [order_id])
        return rows[0]["data"] if rows else None

    def list_orders(self, patient_id=None):
        if patient_id:
            rows = self.sql.query("SELECT data FROM PROVIDER.EHR_ORDER WHERE patient_id = %s ORDER BY updated_at DESC", [patient_id])
        else:
            rows = self.sql.query("SELECT data FROM PROVIDER.EHR_ORDER ORDER BY updated_at DESC")
        return [r["data"] for r in rows]

    def find_order_by_claim(self, claim_id):
        rows = self.sql.query("SELECT data FROM PROVIDER.EHR_ORDER WHERE data:pas:claim_id::string = %s", [claim_id])
        return rows[0]["data"] if rows else None
