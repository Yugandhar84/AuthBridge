# Cortex structured extraction embedded into AI.SP_DTR_AUTOFILL and AI.SP_AI_REVIEW.
# The model only finds facts and copies a verbatim quote; thresholds are applied
# later by the criteria engine, and every quote is re-verified as a substring.
import json as _json
import re as _re

_SCHEMA = {
    "type": "object",
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "linkId": {"type": "string"},
                    "found": {"type": "boolean"},
                    "value": {"type": "string"},
                    "quote": {"type": "string"},
                    "doc_id": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["High", "Medium", "Low"]},
                },
                "required": ["linkId", "found"],
            },
        }
    },
    "required": ["answers"],
}


def _sql_literal(obj):
    """Python -> Snowflake OBJECT/ARRAY constant (for response_format)."""
    if isinstance(obj, dict):
        return "{" + ", ".join("'%s': %s" % (k, _sql_literal(v)) for k, v in obj.items()) + "}"
    if isinstance(obj, list):
        return "[" + ", ".join(_sql_literal(v) for v in obj) + "]"
    if isinstance(obj, bool):
        return "TRUE" if obj else "FALSE"
    if isinstance(obj, (int, float)):
        return str(obj)
    return "'" + str(obj).replace("'", "''") + "'"


def _model(session):
    rows = session.sql("SELECT value FROM AI.APP_CONFIG WHERE key = 'LLM_MODEL'").collect()
    model = rows[0][0] if rows else "claude-haiku-5-5"
    if not _re.match(r"^[a-z0-9.\-]+$", model):
        raise ValueError("Invalid model name in AI.APP_CONFIG")
    return model


def _coerce(item_type, raw):
    if raw is None or raw == "":
        return None
    try:
        if item_type == "boolean":
            return str(raw).strip().lower() in ("true", "yes", "1")
        if item_type == "integer":
            return int(float(raw))
        if item_type == "decimal":
            return float(str(raw).replace("%", ""))
    except ValueError:
        return None
    return raw


def cortex_extract(session, items, notes):
    """items: [{linkId, text, type}]; notes: [{doc_id, title, encounter_date, text}].
    Returns {linkId: {value, quote, doc_id, confidence, method}} for found facts."""
    model = _model(session)
    notes_block = "\n\n".join(
        "<document doc_id=\"%s\" date=\"%s\" title=\"%s\">\n%s\n</document>" % (n["doc_id"], n.get("encounter_date"), n.get("title"), n["text"])
        for n in notes)
    questions = "\n".join("- linkId=%s (type %s): %s" % (i["linkId"], i["type"], i["text"]) for i in items)
    prompt = (
        "You extract facts from a patient's clinical documents to answer a prior authorization questionnaire.\n"
        "Rules:\n"
        "1. Answer only from the documents below. If a fact is not stated, set found=false.\n"
        "2. quote must be copied character-for-character from one document (one or two full sentences).\n"
        "3. doc_id must be the document the quote came from.\n"
        "4. value is the answer only: true/false for boolean, a number for integer/decimal.\n"
        "5. Do not decide whether policy criteria are met.\n\n"
        "Questions:\n" + questions + "\n\nDocuments:\n" + notes_block)
    sql = "SELECT AI_COMPLETE(model => '%s', prompt => ?, response_format => %s) AS r" % (model, _sql_literal({"type": "json", "schema": _SCHEMA}))
    raw = session.sql(sql, params=[prompt]).collect()[0][0]
    data = _json.loads(raw) if isinstance(raw, str) else raw
    types = {i["linkId"]: i["type"] for i in items}
    out = {}
    for a in (data or {}).get("answers", []):
        if not a.get("found") or a.get("linkId") not in types:
            continue
        value = _coerce(types[a["linkId"]], a.get("value"))
        if value is None:
            continue
        out[a["linkId"]] = {"value": value, "quote": a.get("quote"), "doc_id": a.get("doc_id"),
                            "confidence": a.get("confidence") or "Medium", "method": "cortex:" + model}
    return out, model
