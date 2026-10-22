"""Agent endpoints for the payer UI. In cortex mode the request is proxied to a
Snowflake Cortex Agent and its SSE events are simplified for the browser. In
mock mode a scripted answer is streamed from the same data, so the UI can be
built and demoed offline."""

import json
import time

from authbridge_common.letters import denial_letter

AGENTS = {
    "analytics": "ANALYTICS_AGENT",
    "clinical_review": "CLINICAL_REVIEW_AGENT",
    "denial_appeal": "DENIAL_APPEAL_AGENT",
}


def sse(event):
    return "data: %s\n\n" % json.dumps(event)


def _stream_text(text, status=None):
    if status:
        yield sse({"type": "status", "message": status})
    words = text.split(" ")
    for i in range(0, len(words), 6):
        yield sse({"type": "text", "text": " ".join(words[i:i + 6]) + " "})
        time.sleep(0.02)
    yield sse({"type": "done"})


def mock_answer(name, message, repo, pa_id=None):
    if name == "analytics":
        m = repo.metrics()
        rows = [[s["service_code"], s["requests"], s["approved"], s["denied"], s["auto_approved"]] for s in m["by_service"]]
        hours = m["median_hours_to_decision"] or 0
        median = "%.0f minutes" % (hours * 60) if hours < 1 else "%.1f hours" % hours
        waiting = m["open_clinician_reviews"]
        text = ("Across %d requests, %.0f%% of decided requests were approved and %.0f%% were approved automatically. "
                "The median time to a decision was %s, and %.0f%% of decisions met the CMS-0057-F time limits. "
                "%s waiting for a clinician. This is mock mode; connect Snowflake to ask free-form questions through Cortex Analyst."
                % (m["total_requests"], 100 * (m["approval_rate"] or 0), 100 * (m["auto_approval_rate"] or 0), median,
                   100 * (m["sla_compliance"] or 0),
                   "No requests are" if waiting == 0 else ("1 request is" if waiting == 1 else "%d requests are" % waiting)))
        yield from _stream_text(text, "Reading PA metrics")
        yield sse({"type": "table", "result_set": {"columns": ["Service", "Requests", "Approved", "Denied", "Auto-approved"], "rows": rows}})
        return
    case = repo.case(pa_id) if pa_id else None
    if not case:
        yield from _stream_text("Open a case first; this agent answers questions about one request.")
        return
    if name == "clinical_review":
        lines = []
        for c in case["criteria"]:
            if c["node_type"] == "LEAF":
                q = (' Evidence: "%s"' % c["quote"]) if c.get("quote") else " No evidence quote."
                lines.append("%s is %s (section %s).%s" % (c["label"], c["status"].replace("_", " ").lower(), c["policy_section_id"], q))
        text = "Recommendation: %s. %s %s" % (case["request"]["recommendation"].replace("_", " ").lower(),
                                              case["request"].get("reason_text") or "", " ".join(lines))
        yield from _stream_text(text, "Reviewing criteria and evidence")
        return
    if name == "denial_appeal":
        yield from _stream_text(denial_letter(case), "Drafting from the decision record")
        return
    yield from _stream_text("Unknown agent %s." % name)


def cortex_answer(name, message, cortex, pa_id=None, thread_id=None, parent_message_id=None):
    agent = AGENTS[name]
    prompt = message if not pa_id else "Prior authorization request %s. %s" % (pa_id, message)
    for event in cortex.run(agent, prompt, schema="AI", thread_id=thread_id, parent_message_id=parent_message_id):
        yield sse(event)
