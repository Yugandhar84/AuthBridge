# Shared helpers embedded into the Python stored procedures by build_sql.py.
import json as _json


def q(session, sql, params=None):
    rows = session.sql(sql, params=params or []).collect()
    out = []
    for r in rows:
        d = {}
        for k, v in r.as_dict().items():
            if isinstance(v, str) and v[:1] in ("{", "["):
                try:
                    v = _json.loads(v)
                except ValueError:
                    pass
            d[k.lower()] = v
        out.append(d)
    return out


def scalar(session, sql, params=None):
    return session.sql(sql, params=params or []).collect()[0][0]


def _iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


def load_nodes(session, policy_doc_id):
    rows = q(session,
             "SELECT node_id, parent_node_id, node_type, label, fact_name, operator, threshold, on_not_met, "
             "policy_section_id, sort_order FROM PAYER.POLICY_CRITERIA WHERE policy_doc_id = ? ORDER BY sort_order",
             [policy_doc_id])
    for r in rows:
        t = r.get("threshold")
        if isinstance(t, str):
            try:
                r["threshold"] = _json.loads(t)
            except ValueError:
                pass
    return rows


def decide(session, pa_id, admin_ref, code, by, role, reason_text, request_text=None):
    approve = code in ("A1", "A6")
    auth = "AUTH-%s" % scalar(session, "SELECT PAYER.SEQ_AUTH.NEXTVAL") if approve else None
    session.sql(
        "INSERT INTO PAYER.DECISION (pa_id, review_action_code, auth_number, admin_ref_number, auth_period_start, "
        "auth_period_end, reason_text, request_text, decided_by, decider_role, ai_assisted) "
        "SELECT ?, ?, ?, ?, IFF(?, CURRENT_DATE(), NULL), IFF(?, DATEADD(day, 90, CURRENT_DATE()), NULL), ?, ?, ?, ?, TRUE",
        params=[pa_id, code, auth, admin_ref, approve, approve, reason_text, request_text, by, role]).collect()
    row = q(session, "SELECT * FROM PAYER.DECISION WHERE pa_id = ? ORDER BY decided_at DESC LIMIT 1", [pa_id])[0]
    return row


def result_of(pa, decision, result):
    return {
        "pa_id": pa["pa_id"], "claim_id": pa["claim_id"], "status": pa["status"],
        "recommendation": pa["recommendation"], "review_action": decision["review_action_code"],
        "auth_number": decision["auth_number"], "admin_ref": decision["admin_ref_number"],
        "period_start": _iso(decision["auth_period_start"]), "period_end": _iso(decision["auth_period_end"]),
        "reason_text": decision["reason_text"], "request_text": decision["request_text"],
        "missing_info": pa.get("missing_info") or [], "unmet": pa.get("unmet") or [],
        "criteria": (result or {}).get("criteria") or pa.get("criteria") or [],
        "sla_due_at": _iso(pa["sla_due_at"]), "decided_by": decision["decided_by"],
        "provider_org_npi": pa.get("provider_org_npi"), "patient_id": pa["patient_id"], "member_id": pa["member_id"],
    }
