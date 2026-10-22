"""Deterministic criteria engine shared by the payer service (mock mode) and the
Snowflake stored procedures (the generator embeds this file in the SP body).

Rules (PRD 8.6):
- The LLM only extracts facts. Thresholds are applied here, never by a model.
- Three-valued logic: MET / NOT_MET / UNKNOWN.
- AUTO_APPROVE only when the tree is MET and every leaf that satisfies it has a
  verified citation. Anything uncertain becomes PEND. A NOT_MET tree becomes
  RECOMMEND_DENY only if a failing leaf is marked RECOMMEND_DENY; that outcome
  goes to a clinician and is never a denial by itself.

Keep this module standard-library only and free of double dollar signs so it can be
embedded in a Snowflake Python stored procedure.
"""

import re

MET, NOT_MET, UNKNOWN = "MET", "NOT_MET", "UNKNOWN"
AUTO_APPROVE, PEND, RECOMMEND_DENY = "AUTO_APPROVE", "PEND", "RECOMMEND_DENY"


def normalize_space(text):
    return re.sub(r"\s+", " ", text or "").strip()


def verify_quote(quote, doc_text):
    """A citation is valid only if the quote is an exact substring of the
    document (whitespace-normalized). Paraphrases fail on purpose."""
    if not quote or not doc_text:
        return False
    return normalize_space(quote) in normalize_space(doc_text)


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "yes", "y", "1"):
            return True
        if v in ("false", "no", "n", "0"):
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return None


def _to_num(value):
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def compare(value, operator, threshold):
    """Return MET / NOT_MET / UNKNOWN for one leaf."""
    if value is None or value == "":
        return UNKNOWN
    if isinstance(threshold, bool) or (isinstance(threshold, str) and threshold.lower() in ("true", "false")):
        left, right = _to_bool(value), _to_bool(threshold)
        if left is None or right is None:
            return UNKNOWN
        ok = left == right if operator == "=" else left != right
        return MET if ok else NOT_MET
    left, right = _to_num(value), _to_num(threshold)
    if left is None or right is None:
        if operator == "=":
            return MET if str(value).strip().lower() == str(threshold).strip().lower() else NOT_MET
        return UNKNOWN
    ops = {
        ">=": left >= right, ">": left > right, "<=": left <= right,
        "<": left < right, "=": left == right, "!=": left != right,
    }
    if operator not in ops:
        return UNKNOWN
    return MET if ops[operator] else NOT_MET


def _combine(node_type, statuses):
    if node_type == "AND":
        if NOT_MET in statuses:
            return NOT_MET
        return MET if statuses and all(s == MET for s in statuses) else UNKNOWN
    if node_type == "OR":
        if MET in statuses:
            return MET
        return NOT_MET if statuses and all(s == NOT_MET for s in statuses) else UNKNOWN
    raise ValueError("unknown node type " + str(node_type))


def evaluate(nodes, facts):
    """Evaluate a criteria tree.

    nodes: list of dicts with node_id, parent_node_id, node_type (AND|OR|LEAF),
           label, fact_name, operator, threshold, on_not_met, policy_section_id,
           sort_order.
    facts: {fact_name: {"value": ..., "quote": str|None, "doc_id": str|None,
            "verified": bool, "origin": "auto"|"override"|"manual"}}
    """
    by_id = {n["node_id"]: dict(n) for n in nodes}
    children = {}
    roots = []
    for n in sorted(by_id.values(), key=lambda x: (x.get("sort_order") or 0, x["node_id"])):
        parent = n.get("parent_node_id")
        if parent:
            children.setdefault(parent, []).append(n["node_id"])
        else:
            roots.append(n["node_id"])
    if len(roots) != 1:
        raise ValueError("criteria tree must have exactly one root, found %d" % len(roots))

    results = {}

    def visit(node_id, depth):
        node = by_id[node_id]
        if node["node_type"] == "LEAF":
            fact = facts.get(node.get("fact_name")) or {}
            status = compare(fact.get("value"), node.get("operator"), node.get("threshold"))
            results[node_id] = dict(
                node, depth=depth, status=status, value=fact.get("value"),
                quote=fact.get("quote"), doc_id=fact.get("doc_id"),
                citation_verified=bool(fact.get("verified")), origin=fact.get("origin"),
            )
            return status
        statuses = [visit(c, depth + 1) for c in children.get(node_id, [])]
        status = _combine(node["node_type"], statuses)
        results[node_id] = dict(node, depth=depth, status=status)
        return status

    root_status = visit(roots[0], 0)

    def satisfying_leaves(node_id):
        r = results[node_id]
        if r["node_type"] == "LEAF":
            return [node_id]
        kids = children.get(node_id, [])
        if r["node_type"] == "OR":
            for c in kids:
                if results[c]["status"] == MET:
                    return satisfying_leaves(c)
            return []
        out = []
        for c in kids:
            out.extend(satisfying_leaves(c))
        return out

    def failing_leaves(node_id):
        r = results[node_id]
        if r["node_type"] == "LEAF":
            return [node_id] if r["status"] == NOT_MET else []
        out = []
        for c in children.get(node_id, []):
            if results[c]["status"] == NOT_MET:
                out.extend(failing_leaves(c))
        return out

    leaves = [r for r in results.values() if r["node_type"] == "LEAF"]
    unknown = [r for r in leaves if r["status"] == UNKNOWN]
    missing_info = []
    unmet = []

    if root_status == MET:
        support = [results[i] for i in satisfying_leaves(roots[0])]
        unverified = [r for r in support if not r["citation_verified"]]
        if unverified:
            recommendation = PEND
            missing_info = [
                "Supporting documentation for: %s (section %s)" % (r["label"], r["policy_section_id"])
                for r in unverified
            ]
            reason = "Criteria appear to be met, but %d answer(s) lack a verifiable quote from the submitted records." % len(unverified)
        else:
            recommendation = AUTO_APPROVE
            reason = "All required criteria are met, each backed by a verified quote from the submitted records."
    elif root_status == UNKNOWN:
        recommendation = PEND
        missing_info = [
            "Documentation of: %s (section %s)" % (r["label"], r["policy_section_id"]) for r in unknown
        ]
        reason = "Some criteria could not be assessed from the submitted information."
    else:
        failing = [results[i] for i in failing_leaves(roots[0])]
        unmet = [
            "%s (section %s): documented value %s" % (r["label"], r["policy_section_id"], _fmt(r["value"]))
            for r in failing
        ]
        if any(r.get("on_not_met") == RECOMMEND_DENY for r in failing):
            recommendation = RECOMMEND_DENY
            reason = "The documented values do not meet the policy criteria. A clinician must review before any denial."
        else:
            recommendation = PEND
            missing_info = [
                "Documentation that would satisfy: %s (section %s)" % (r["label"], r["policy_section_id"])
                for r in failing
            ]
            reason = "Criteria are not yet met; additional documentation may satisfy them."

    ordered = [results[n["node_id"]] for n in sorted(by_id.values(), key=lambda x: (x.get("sort_order") or 0))]
    return {
        "recommendation": recommendation,
        "root_status": root_status,
        "reason_text": reason,
        "missing_info": missing_info,
        "unmet": unmet,
        "criteria": [_public(r) for r in ordered],
    }


def _fmt(value):
    if value is None:
        return "not documented"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def _public(r):
    keys = ("node_id", "parent_node_id", "node_type", "label", "fact_name", "operator", "threshold",
            "on_not_met", "policy_section_id", "depth", "status", "value", "quote", "doc_id",
            "citation_verified", "origin")
    return {k: r.get(k) for k in keys}
