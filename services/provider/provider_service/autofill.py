"""DTR auto-fill: propose questionnaire answers with chart evidence.

mock:   pattern extractor over the synthetic notes (authbridge_common.mock_ai)
cortex: CALL AI.SP_DTR_AUTOFILL, which retrieves the patient's notes and asks
        AI_COMPLETE for structured answers with verbatim quotes.
Either way every quote is re-verified here as an exact substring of the note,
and answers whose quote fails are dropped (left for the clinician).
"""

from authbridge_common.criteria import verify_quote
from authbridge_common.mock_ai import extract_facts


def autofill(settings, sql, patient_id, items, notes):
    if settings.use_cortex:
        raw = sql.call("AI.SP_DTR_AUTOFILL", patient_id, items, [n["doc_id"] for n in notes]) or {}
        proposals = raw.get("answers", raw) if isinstance(raw, dict) else {}
        method = "cortex"
    else:
        proposals = extract_facts([i["linkId"] for i in items], notes)
        method = "mock-pattern"
    link_ids = [i["linkId"] for i in items]
    by_doc = {n["doc_id"]: n for n in notes}
    answers, rejected = {}, []
    for link_id, p in (proposals or {}).items():
        if link_id not in link_ids or p.get("value") is None:
            continue
        doc = by_doc.get(p.get("doc_id"))
        if not verify_quote(p.get("quote"), doc["text"] if doc else None):
            rejected.append(link_id)
            continue
        answers[link_id] = {
            "value": p["value"], "quote": p["quote"], "doc_id": p["doc_id"],
            "doc_title": doc.get("title"), "confidence": p.get("confidence") or "Medium",
            "origin": "auto", "method": p.get("method", method),
        }
    return answers, rejected
