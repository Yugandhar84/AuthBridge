"""In-memory payer backend (AUTHBRIDGE_BACKEND=mock).

Mirrors the Snowflake stored procedures in snowflake/sql so the app runs with no
account. The decision logic is the shared criteria engine; the Snowflake SPs
embed the same file, so both backends decide the same way.
"""

import statistics
import threading
from datetime import datetime, timedelta, timezone

from authbridge_common import criteria as engine
from authbridge_common import history
from authbridge_common.fhir import new_id, today
from authbridge_common.seed import load_seed, policy_sections

QUESTIONNAIRE_BASE = "https://authbridge.example/fhir/Questionnaire/"


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


class MockPayerRepo:
    def __init__(self, settings):
        seed = load_seed(settings.seed_dir)
        p = seed["payer"]
        self.payer = p["payer"]
        self.plans = {x["plan_id"]: x for x in p["plans"]}
        self.members = p["members"]
        self.rules = p["service_pa_rules"]
        self.criteria = p["policy_criteria"]
        self.gold = {(g["ordering_npi"], g["service_code"]): g for g in p["gold_card_status"]}
        self.catalog = {c["code"]: c for c in p["catalog"]}
        self.questionnaires = seed["questionnaires"]
        self.policies = seed["policies"]
        self.lock = threading.RLock()
        self.requests = {}
        self.reviews = {}
        self.decisions = []
        self.audit = []
        self.exchanges = []
        self.subscriptions = []
        self.crd_log = []
        self._seq = 1000
        for h in history.generate():
            self.requests[h["pa_id"]] = dict(h, historical=True, answers={}, documents=[], criteria=[])
            self.decisions.append({
                "decision_id": new_id("dec"), "pa_id": h["pa_id"], "review_action_code": h["review_action_code"],
                "decided_by": h["decided_by"], "decider_role": h["decider_role"], "decided_at": h["decided_at"],
                "ai_assisted": True, "reason_text": None,
            })

    # ---- helpers -------------------------------------------------------
    def _next(self, prefix):
        with self.lock:
            self._seq += 1
            return "%s-%d" % (prefix, self._seq)

    def _member(self, member_id, on_date=None):
        on_date = on_date or today()
        for m in self.members:
            if m["member_id"] == member_id:
                active = m["status"] == "active" and m["eff_start"] <= on_date and (m["eff_end"] or "9999") >= on_date
                return m, active
        return None, False

    def _rule(self, service_code, plan_id):
        best = None
        for r in self.rules:
            if r["service_code"] == service_code and r["plan_id"] in (None, plan_id):
                if best is None or (r["plan_id"] is not None and best["plan_id"] is None):
                    best = r
        return best

    def _nodes(self, policy_doc_id):
        return [n for n in self.criteria if n["policy_doc_id"] == policy_doc_id]

    # ---- CRD -------------------------------------------------------------
    def crd_evaluate(self, member_id, patient_id, service_code, code_system, ordering_npi, hook):
        assertion = "CA-%s-%s" % (today().replace("-", ""), self._next("x").split("-")[1])
        member, active = self._member(member_id)
        base = {"coverage_assertion_id": assertion, "date": today(), "service_code": service_code}
        if not member:
            res = dict(base, covered="not-covered", reason_text="No member found for this coverage", reason_code=None)
        elif not active:
            res = dict(base, covered="not-covered", reason_text="Coverage is not active on the date of service")
        else:
            plan = self.plans[member["plan_id"]]
            rule = self._rule(service_code, plan["plan_id"])
            base.update(plan_id=plan["plan_id"], line_of_business=plan["line_of_business"])
            if not rule:
                res = dict(base, covered="conditional", pa_needed="conditional",
                           reason_text="Service not found in the plan's prior authorization list; call the plan")
            elif not rule["pa_required"]:
                res = dict(base, covered="covered", pa_needed="no-auth", rule_id=rule["rule_id"])
            else:
                gold = self.gold.get((ordering_npi, service_code))
                if gold and gold["status"] == "GOLD" and rule["gold_card_eligible"]:
                    res = dict(base, covered="covered", pa_needed="satisfied", reason_code="gold-card",
                               reason_text="Ordering practitioner holds a gold card for this service",
                               satisfied_pa_id="%s-%s" % (gold["satisfied_pa_prefix"], assertion[-4:]),
                               rule_id=rule["rule_id"], policy_doc_id=rule["policy_doc_id"])
                else:
                    q = self.questionnaires.get(rule["questionnaire_id"])
                    res = dict(base, covered="covered", pa_needed="auth-needed",
                               doc_needed="clinical" if rule["doc_required"] else None,
                               doc_purpose="withpa" if rule["doc_required"] else None,
                               questionnaire_id=rule["questionnaire_id"],
                               questionnaire_url=("%s|%s" % (q["url"], q["version"])) if q else None,
                               rule_id=rule["rule_id"], policy_doc_id=rule["policy_doc_id"])
        if hook == "order-select":
            # order-select SHALL NOT signal documentation needs (CRD 2.2)
            res.pop("doc_needed", None)
            res.pop("doc_purpose", None)
            res.pop("questionnaire_url", None)
        with self.lock:
            self.crd_log.append(dict(res, member_id=member_id, patient_id=patient_id, ordering_npi=ordering_npi, hook=hook))
        return res

    # ---- DTR -------------------------------------------------------------
    def get_questionnaire(self, questionnaire_id):
        return self.questionnaires.get(questionnaire_id)

    def questionnaire_policy(self, questionnaire_id):
        for r in self.rules:
            if r["questionnaire_id"] == questionnaire_id:
                return r["policy_doc_id"]
        return None

    def completeness(self, questionnaire_id, facts):
        policy = self.questionnaire_policy(questionnaire_id)
        if not policy:
            return None
        return dict(engine.evaluate(self._nodes(policy), facts), policy_doc_id=policy)

    # ---- PAS -------------------------------------------------------------
    def find_pa_by_claim(self, claim_id):
        for r in self.requests.values():
            if r.get("claim_id") == claim_id:
                return r["pa_id"]
        return None

    def pas_submit(self, req):
        member, active = self._member(req["member_id"])
        if not member or not active:
            return {"error": "no-active-coverage", "message": "No active coverage for member %s" % req["member_id"]}
        plan = self.plans[member["plan_id"]]
        rule = self._rule(req["service_code"], plan["plan_id"])
        now = _utcnow()
        sla_hours = 72 if req.get("priority") == "expedited" else 168

        with self.lock:
            existing = self.requests.get(req.get("related_pa_id")) if req.get("related_pa_id") else None
            pa_id = existing["pa_id"] if existing else self._next("PA")
            docs = {d["doc_id"]: d for d in (existing or {}).get("documents", [])}
            docs.update({d["doc_id"]: d for d in req.get("documents", [])})

            facts = {}
            for name, ans in (req.get("answers") or {}).items():
                doc = docs.get(ans.get("doc_id"))
                facts[name] = dict(ans, verified=engine.verify_quote(ans.get("quote"), doc["text"] if doc else None))

            if not rule or not rule["pa_required"]:
                result = {"recommendation": engine.AUTO_APPROVE, "reason_text": "Prior authorization is not required for this service.",
                          "criteria": [], "missing_info": [], "unmet": []}
            else:
                result = engine.evaluate(self._nodes(rule["policy_doc_id"]), facts)

            rec = result["recommendation"]
            record = {
                "pa_id": pa_id, "claim_id": req["claim_id"], "patient_id": req["patient_id"], "member_id": req["member_id"],
                "plan_id": plan["plan_id"], "line_of_business": plan["line_of_business"],
                "ordering_npi": req["ordering_npi"], "provider_org_npi": req.get("provider_org_npi"),
                "service_code": req["service_code"], "code_system": req["code_system"],
                "service_display": req.get("service_display") or self.catalog.get(req["service_code"], {}).get("display"),
                "policy_doc_id": rule["policy_doc_id"] if rule else None, "questionnaire_id": req.get("questionnaire_id"),
                "icd10_codes": req.get("icd10", []), "priority": req.get("priority", "standard"),
                "coverage_assertion_id": req.get("coverage_assertion_id"),
                "submitted_at": (existing or {}).get("submitted_at") or now.isoformat(),
                "sla_due_at": (existing or {}).get("sla_due_at") or (now + timedelta(hours=sla_hours)).isoformat(),
                "answers": req.get("answers", {}), "documents": list(docs.values()),
                "criteria": result["criteria"], "recommendation": rec, "reason_text": result["reason_text"],
                "missing_info": result["missing_info"], "unmet": result["unmet"],
                "version": (existing or {}).get("version", 0) + 1, "historical": False,
                "admin_ref": (existing or {}).get("admin_ref") or self._next("REF"),
            }
            self.audit.append({
                "audit_id": new_id("aud"), "pa_id": pa_id, "agent_name": "CRITERIA_ENGINE", "model": "deterministic",
                "policy_version": record["policy_doc_id"], "output": result, "recommendation": rec,
                "ai_assisted": any(a.get("origin") == "auto" for a in record["answers"].values()),
                "created_at": now.isoformat(),
            })
            if rec == engine.AUTO_APPROVE:
                record["status"] = "APPROVED"
                decision = self._decide(record, "A1", "SYSTEM", "SYSTEM", result["reason_text"])
            elif rec == engine.PEND:
                record["status"] = "PENDED"
                decision = self._decide(record, "A4", "SYSTEM", "SYSTEM", result["reason_text"],
                                        request_text="; ".join(result["missing_info"]))
            else:
                record["status"] = "CLINICIAN_REVIEW"
                decision = self._decide(record, "A4", "SYSTEM", "SYSTEM",
                                        "Pended for clinical review. " + result["reason_text"],
                                        request_text="A clinician is reviewing this request. No action is needed unless more records are available.")
            self.requests[pa_id] = record
        return self._result(record, decision)

    def _decide(self, record, action, by, role, reason_text, request_text=None):
        now = _utcnow()
        decision = {
            "decision_id": new_id("dec"), "pa_id": record["pa_id"], "review_action_code": action,
            "auth_number": self._next("AUTH") if action in ("A1", "A6") else None,
            "admin_ref_number": record["admin_ref"],
            "auth_period_start": today() if action in ("A1", "A6") else None,
            "auth_period_end": (now + timedelta(days=90)).date().isoformat() if action in ("A1", "A6") else None,
            "reason_text": reason_text, "request_text": request_text, "decided_by": by, "decider_role": role,
            "ai_assisted": True, "decided_at": now.isoformat(),
        }
        self.decisions.append(decision)
        record["last_decision"] = decision
        return decision

    def _result(self, record, decision):
        return {
            "pa_id": record["pa_id"], "claim_id": record["claim_id"], "status": record["status"],
            "recommendation": record["recommendation"], "review_action": decision["review_action_code"],
            "auth_number": decision["auth_number"], "admin_ref": decision["admin_ref_number"],
            "period_start": decision["auth_period_start"], "period_end": decision["auth_period_end"],
            "reason_text": decision["reason_text"], "request_text": decision.get("request_text"),
            "missing_info": record.get("missing_info", []), "unmet": record.get("unmet", []),
            "criteria": record.get("criteria", []), "sla_due_at": record["sla_due_at"],
            "decided_by": decision["decided_by"], "provider_org_npi": record.get("provider_org_npi"),
            "patient_id": record["patient_id"], "member_id": record["member_id"],
        }

    # ---- Clinician workbench ------------------------------------------------
    def record_decision(self, pa_id, action, reviewer, role, reason_text, request_text=None):
        with self.lock:
            rec = self.requests.get(pa_id)
            if not rec or rec.get("historical"):
                raise KeyError(pa_id)
            if action == "DENY":
                if role != "MEDICAL_DIRECTOR":
                    raise PermissionError("Only a medical director can issue a denial (A3).")
                if not reviewer or not reason_text:
                    raise ValueError("A denial needs a named signer and a specific reason.")
                rec["status"] = "DENIED"
                d = self._decide(rec, "A3", reviewer, role, reason_text)
            elif action == "APPROVE":
                rec["status"] = "APPROVED"
                d = self._decide(rec, "A1", reviewer, role, reason_text or "Approved after clinical review.")
            elif action == "PEND":
                rec["status"] = "PENDED"
                d = self._decide(rec, "A4", reviewer, role, reason_text or "More information requested.",
                                 request_text=request_text or reason_text)
            else:
                raise ValueError("action must be APPROVE, PEND or DENY")
            self.audit.append({"audit_id": new_id("aud"), "pa_id": pa_id, "agent_name": "HUMAN", "model": None,
                               "recommendation": rec["recommendation"], "output": {"action": action, "reason": reason_text},
                               "ai_assisted": True, "human_actor": reviewer, "created_at": _utcnow().isoformat()})
            return self._result(rec, d)

    def override_criterion(self, pa_id, node_id, status, reason, reviewer):
        with self.lock:
            rec = self.requests[pa_id]
            for c in rec["criteria"]:
                if c["node_id"] == node_id:
                    c["reviewer_override"] = status
                    c["override_reason"] = reason
                    c["override_by"] = reviewer
                    return c
        raise KeyError(node_id)

    def queue(self):
        rows = []
        for r in self.requests.values():
            if r.get("historical"):
                continue
            rows.append({k: r.get(k) for k in ("pa_id", "member_id", "patient_id", "service_code", "service_display", "priority",
                                                "status", "recommendation", "submitted_at", "sla_due_at", "ordering_npi", "line_of_business")})
        return sorted(rows, key=lambda x: x["sla_due_at"])

    def case(self, pa_id):
        r = self.requests.get(pa_id)
        if not r:
            return None
        policy = r.get("policy_doc_id")
        return {
            "request": {k: v for k, v in r.items() if k not in ("criteria", "documents", "answers")},
            "criteria": r.get("criteria", []),
            "answers": r.get("answers", {}),
            "documents": r.get("documents", []),
            "decisions": [d for d in self.decisions if d["pa_id"] == pa_id],
            "audit": [a for a in self.audit if a["pa_id"] == pa_id],
            "policy_sections": policy_sections(policy, self.policies[policy]) if policy in self.policies else [],
            "decision": r.get("last_decision"),
        }

    # ---- Analytics -----------------------------------------------------------
    def metrics(self):
        reqs = list(self.requests.values())
        final = {}
        for d in self.decisions:
            if d["review_action_code"] in ("A1", "A3", "A6"):
                final.setdefault(d["pa_id"], d)
        total = len(reqs)
        decided = len(final)
        approved = sum(1 for d in final.values() if d["review_action_code"] in ("A1", "A6"))
        denied = sum(1 for d in final.values() if d["review_action_code"] == "A3")
        auto = sum(1 for d in final.values() if d["decided_by"] == "SYSTEM" and d["review_action_code"] == "A1")
        hours, sla_met, sla_total = [], 0, 0
        by_priority = {"standard": [], "expedited": []}
        for r in reqs:
            d = final.get(r["pa_id"])
            if not d:
                continue
            h = (datetime.fromisoformat(d["decided_at"]) - datetime.fromisoformat(r["submitted_at"])).total_seconds() / 3600
            hours.append(h)
            by_priority.setdefault(r["priority"], []).append(h)
            sla_total += 1
            if datetime.fromisoformat(d["decided_at"]) <= datetime.fromisoformat(r["sla_due_at"]):
                sla_met += 1
        by_service = {}
        for r in reqs:
            s = by_service.setdefault(r["service_code"], {"service_code": r["service_code"], "service_display": r.get("service_display"),
                                                           "requests": 0, "approved": 0, "denied": 0, "auto_approved": 0})
            s["requests"] += 1
            d = final.get(r["pa_id"])
            if d and d["review_action_code"] in ("A1", "A6"):
                s["approved"] += 1
                if d["decided_by"] == "SYSTEM":
                    s["auto_approved"] += 1
            if d and d["review_action_code"] == "A3":
                s["denied"] += 1
        appealed = [r for r in reqs if r.get("appealed")]
        overturned = [r for r in appealed if r.get("appeal_outcome") == "OVERTURNED"]
        return {
            "total_requests": total,
            "decided": decided,
            "approval_rate": round(approved / decided, 3) if decided else None,
            "denial_rate": round(denied / decided, 3) if decided else None,
            "auto_approval_rate": round(auto / decided, 3) if decided else None,
            "median_hours_to_decision": round(statistics.median(hours), 2) if hours else None,
            "median_hours_standard": round(statistics.median(by_priority["standard"]), 2) if by_priority["standard"] else None,
            "median_hours_expedited": round(statistics.median(by_priority["expedited"]), 2) if by_priority["expedited"] else None,
            "sla_compliance": round(sla_met / sla_total, 3) if sla_total else None,
            "open_clinician_reviews": sum(1 for r in reqs if r.get("status") == "CLINICIAN_REVIEW"),
            "open_pends": sum(1 for r in reqs if r.get("status") == "PENDED"),
            "appeal_overturn_rate": round(len(overturned) / len(appealed), 3) if appealed else None,
            "by_service": sorted(by_service.values(), key=lambda x: -x["requests"]),
            "gold_card": list(self.gold.values()),
        }

    # ---- Exchanges and subscriptions -------------------------------------------
    def log_exchange(self, direction, endpoint, correlation_id, payload, validation=None):
        with self.lock:
            self.exchanges.append({"payload_id": new_id("raw"), "direction": direction, "endpoint": endpoint,
                                   "correlation_id": correlation_id, "payload": payload,
                                   "validation_outcome": validation, "received_at": _utcnow().isoformat()})

    def list_exchanges(self, correlation_id=None, limit=50):
        rows = [e for e in self.exchanges if not correlation_id or e["correlation_id"] == correlation_id]
        return rows[-limit:][::-1]

    def add_subscription(self, sub_id, org_identifier, endpoint, resource):
        with self.lock:
            self.subscriptions = [s for s in self.subscriptions if s["endpoint"] != endpoint]
            self.subscriptions.append({"subscription_id": sub_id, "org_identifier": org_identifier,
                                       "endpoint": endpoint, "status": "active", "fhir": resource})

    def list_subscriptions(self, org_identifier=None):
        return [s for s in self.subscriptions if not org_identifier or s["org_identifier"] in (None, org_identifier)]

    def policy_sections(self, policy_id):
        return policy_sections(policy_id, self.policies[policy_id]) if policy_id in self.policies else []
