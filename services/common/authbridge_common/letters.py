"""Template letters built only from structured data (codes, dates, criteria).

Used directly in mock mode and as the factual skeleton the Cortex Denial /
Appeal agent must keep in Snowflake mode (PRD FR-10.1: administrative fields
come from tables, never from the model).
"""


def _criteria_lines(criteria, statuses):
    lines = []
    for c in criteria:
        if c.get("node_type") == "LEAF" and c.get("status") in statuses:
            value = c.get("value")
            shown = "not documented" if value is None else value
            lines.append("- %s (policy section %s). Documented: %s." % (c["label"], c["policy_section_id"], shown))
    return lines


def denial_letter(case):
    req = case["request"]
    decision = case.get("decision") or {}
    lines = [
        "Prior authorization decision: NOT CERTIFIED (X12 A3)",
        "",
        "Member: %s   Request: %s   Service: %s %s" % (req.get("member_id"), req.get("pa_id"), req.get("service_code"), req.get("service_display") or ""),
        "Ordering practitioner NPI: %s" % req.get("ordering_npi"),
        "Policy applied: %s" % req.get("policy_doc_id"),
        "",
        "Why the request was not approved:",
    ]
    lines += _criteria_lines(case.get("criteria", []), ("NOT_MET", "UNKNOWN")) or ["- See reviewer note."]
    if decision.get("reason_text"):
        lines += ["", "Reviewer note: %s" % decision["reason_text"]]
    lines += [
        "",
        "What would change this decision:",
        "Submit records that show the criteria above are met, for example test results or treatment notes dated within the last 12 months.",
        "",
        "This decision was made by a licensed clinician (%s). AI was used to organize the evidence; it did not make this decision." % (decision.get("decided_by") or "medical director"),
        "",
        "Your appeal rights: you or the ordering practitioner may request a reconsideration or peer-to-peer discussion. Reply through the provider portal within 60 days of this notice.",
    ]
    return "\n".join(lines)


def appeal_draft(case, practitioner_name):
    req = case["request"]
    met = _criteria_lines(case.get("criteria", []), ("MET",))
    gaps = _criteria_lines(case.get("criteria", []), ("NOT_MET", "UNKNOWN"))
    evidence = []
    for c in case.get("criteria", []):
        if c.get("node_type") == "LEAF" and c.get("quote"):
            evidence.append('- "%s" (%s)' % (c["quote"], c.get("doc_id")))
    lines = [
        "Request for reconsideration – prior authorization %s" % req.get("pa_id"),
        "",
        "Service: %s %s" % (req.get("service_code"), req.get("service_display") or ""),
        "Member ID: %s" % req.get("member_id"),
        "",
        "I am requesting reconsideration of the decision on this request. The patient's records document the following:",
    ]
    lines += evidence or ["- [Add chart evidence here]"]
    if met:
        lines += ["", "Criteria already met:"] + met
    if gaps:
        lines += ["", "Criteria the plan found unmet, with my clinical response:"] + [g + " Response: [explain]" for g in gaps]
    lines += ["", "Sincerely,", practitioner_name or "[Ordering practitioner]", "", "Draft prepared with AI assistance. Review and edit before sending."]
    return "\n".join(lines)
