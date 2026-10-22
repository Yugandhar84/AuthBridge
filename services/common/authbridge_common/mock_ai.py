"""Offline stand-in for the Cortex DTR Auto-fill Agent.

Used when AUTHBRIDGE_AI=mock so the whole flow runs without Snowflake. It finds
facts in the synthetic notes with simple patterns and returns the sentence it
matched as the evidence quote, so citations are real substrings and pass the
same verification as Cortex output. Replace with the Cortex path
(AI.SP_DTR_AUTOFILL) for the real demo.
"""

import re

from .fhir import split_sentences


def _sentences(notes):
    for note in notes:
        for s in split_sentences(note["text"]):
            yield note, s


def _number(pattern, cast=float):
    rx = re.compile(pattern, re.IGNORECASE)

    def finder(notes):
        best = None
        for note, sent in _sentences(notes):
            m = rx.search(sent)
            if m:
                value = cast(m.group(1))
                # prefer the largest/most recent figure for "weeks"-style facts
                if best is None or note["encounter_date"] >= best["note"]["encounter_date"]:
                    best = {"value": value, "quote": sent, "note": note}
        return best
    return finder


def _flag(positive, negative):
    pos = re.compile(positive, re.IGNORECASE)
    neg = re.compile(negative, re.IGNORECASE)

    def finder(notes):
        found_neg = None
        for note, sent in _sentences(notes):
            if neg.search(sent):
                found_neg = found_neg or {"value": False, "quote": sent, "note": note}
            elif pos.search(sent):
                return {"value": True, "quote": sent, "note": note}
        return found_neg
    return finder


def _f2f_before_sleep_test(notes):
    f2f = None
    test = None
    for note, sent in _sentences(notes):
        if re.search(r"face-to-face evaluation", sent, re.I) and f2f is None:
            f2f = (note, sent)
        if re.search(r"polysomnography performed", sent, re.I) and test is None:
            test = (note, sent)
    if not f2f:
        return None
    if test and f2f[0]["encounter_date"] < test[0]["encounter_date"]:
        return {"value": True, "quote": f2f[1], "note": f2f[0]}
    return {"value": None if not test else False, "quote": f2f[1], "note": f2f[0]}


def _weeks_conservative(notes):
    rx = re.compile(r"(\d+) weeks of (?:supervised physical therapy|physical therapy|naproxen|nsaids|conservative care)", re.I)
    rx2 = re.compile(r"after (\d+) weeks of", re.I)
    best = None
    for note, sent in _sentences(notes):
        m = rx.search(sent) or rx2.search(sent)
        if m:
            v = int(m.group(1))
            if best is None or v > best["value"]:
                best = {"value": v, "quote": sent, "note": note}
    return best


FINDERS = {
    "f2f_before_sleep_test": _f2f_before_sleep_test,
    "ahi": _number(r"\bAHI\)?\s*(?:of|was|=|:)?\s*(\d+(?:\.\d+)?)"),
    "qualifying_symptom": _flag(r"excessive daytime sleepiness|impaired cognition|insomnia|hypertension", r"denies daytime sleepiness"),
    "red_flag": _flag(r"saddle anesthesia|urinary retention|cauda equina|foot drop|progressive weakness",
                      r"\bno (?:bowel or bladder changes|saddle anesthesia)"),
    "conservative_weeks": _weeks_conservative,
    "spo2_rest": _number(r"resting room-air SpO2 (\d+(?:\.\d+)?)%"),
    "spo2_exercise": _number(r"walk test[^.]*?lowest SpO2 (\d+(?:\.\d+)?)%"),
    "spo2_sleep": _number(r"overnight oximetry: nadir SpO2 (\d+(?:\.\d+)?)%"),
    "weeks_at_maintenance": _number(r"(\d+) weeks at the .*?maintenance dose", int),
    "weight_loss_pct": _number(r"\((\d+(?:\.\d+)?)% loss\)"),
}


def extract_facts(fact_names, notes):
    """Return {fact_name: {value, quote, doc_id, confidence, method}} for the facts found."""
    out = {}
    for name in fact_names:
        finder = FINDERS.get(name)
        if not finder:
            continue
        hit = finder(notes)
        if hit and hit.get("value") is not None:
            out[name] = {
                "value": hit["value"],
                "quote": hit["quote"],
                "doc_id": hit["note"]["doc_id"],
                "confidence": "High",
                "method": "mock-pattern",
            }
    return out
