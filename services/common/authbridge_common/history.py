"""Deterministic synthetic history of past PA requests, so analytics and the
CMS metrics dashboard have data on day 1. Used by mock mode and by the SQL
seed generator, so both backends show the same numbers."""

import random
from datetime import datetime, timedelta

SERVICES = [
    ("72148", "CPT", "MRI lumbar spine without contrast", "POL-DEMO-LSMRI-v1"),
    ("E0601", "HCPCS", "CPAP device", "POL-DEMO-PAP-v1"),
    ("E1390", "HCPCS", "Oxygen concentrator", "POL-DEMO-O2-v1"),
    ("SEMAGLUTIDE-2.4", "DEMO-DRUG", "Semaglutide 2.4 mg (continuation)", "POL-DEMO-GLP1-v1"),
]
NPIS = ["1234567893", "1477589632", "1619934211", "1902847365"]


def generate(n=80, seed=42, end=None):
    rnd = random.Random(seed)
    end = end or datetime(2026, 10, 15, 17, 0, 0)
    rows = []
    for i in range(n):
        code, system, display, policy = rnd.choice(SERVICES)
        submitted = end - timedelta(days=rnd.uniform(1, 120), hours=rnd.uniform(0, 10))
        expedited = rnd.random() < 0.2
        sla_hours = 72 if expedited else 168
        roll = rnd.random()
        if roll < 0.55:
            rec, action, status, by, hours = "AUTO_APPROVE", "A1", "APPROVED", "SYSTEM", rnd.uniform(0.001, 0.02)
        elif roll < 0.80:
            rec, action, status, by, hours = "PEND", "A1", "APPROVED", "nurse.jordan", rnd.uniform(6, 120)
        elif roll < 0.92:
            rec, action, status, by, hours = "RECOMMEND_DENY", "A3", "DENIED", "dr.chen", rnd.uniform(10, 160)
        else:
            rec, action, status, by, hours = "RECOMMEND_DENY", "A1", "APPROVED", "dr.chen", rnd.uniform(10, 90)
        if rnd.random() < 0.06:
            hours = sla_hours + rnd.uniform(2, 30)  # a few SLA misses
        decided = submitted + timedelta(hours=hours)
        member = "H%06d" % (200000 + i)
        rows.append({
            "pa_id": "PA-H%04d" % i,
            "member_id": member,
            "patient_id": "hist-%04d" % i,
            "plan_id": "DEMO-MA-01" if rnd.random() < 0.75 else "DEMO-COMM-01",
            "ordering_npi": rnd.choice(NPIS),
            "service_code": code,
            "code_system": system,
            "service_display": display,
            "policy_doc_id": policy,
            "priority": "expedited" if expedited else "standard",
            "status": status,
            "recommendation": rec,
            "review_action_code": action,
            "decided_by": by,
            "decider_role": "SYSTEM" if by == "SYSTEM" else ("MEDICAL_DIRECTOR" if by == "dr.chen" else "UM_NURSE"),
            "submitted_at": submitted.replace(microsecond=0).isoformat(),
            "sla_due_at": (submitted + timedelta(hours=sla_hours)).replace(microsecond=0).isoformat(),
            "decided_at": decided.replace(microsecond=0).isoformat(),
            "ai_assisted": True,
            "appealed": action == "A3" and rnd.random() < 0.5,
            "appeal_outcome": None,
        })
        if rows[-1]["appealed"]:
            rows[-1]["appeal_outcome"] = "OVERTURNED" if rnd.random() < 0.6 else "UPHELD"
    return rows
