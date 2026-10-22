"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AgentChat } from "@/components/AgentChat";
import { CriteriaTree } from "@/components/CriteriaTree";
import { ErrorNote, Highlighted, Section, StatusPill } from "@/components/ui";
import { get, payer, send } from "@/lib/api";
import { formatHours, hoursLeft } from "@/lib/status";
import type { Case, Criterion } from "@/lib/types";

const REVIEWERS = [
  { id: "nurse.jordan", name: "Jordan Lee, RN (utilization review)", role: "UM_NURSE" },
  { id: "dr.chen", name: "Dr. Mei Chen (medical director)", role: "MEDICAL_DIRECTOR" },
];

export default function CaseReview() {
  const { id } = useParams<{ id: string }>();
  const [c, setCase] = useState<Case | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reviewer, setReviewer] = useState(REVIEWERS[0]);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [letter, setLetter] = useState<string | null>(null);

  const load = useCallback(() => get<Case>(payer(`/internal/cases/${id}`)).then(setCase).catch((e) => setError(e.message)), [id]);
  useEffect(() => {
    load();
  }, [load]);

  async function decide(action: "APPROVE" | "PEND" | "DENY") {
    setBusy(true);
    setError(null);
    try {
      await send(payer(`/internal/cases/${id}/decision`), {
        action,
        reviewer: reviewer.id,
        role: reviewer.role,
        reason_text: reason,
        request_text: action === "PEND" ? reason : undefined,
      });
      setReason("");
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function override(node: Criterion, status: string) {
    const why = window.prompt(`Why set "${node.label}" to ${status.toLowerCase().replace("_", " ")}?`);
    if (!why) return;
    try {
      await send(payer(`/internal/cases/${id}/criteria/${node.node_id}/override`), { status, reason: why, reviewer: reviewer.id });
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (!c) return <ErrorNote error={error} />;
  const r = c.request;
  const open = ["PENDED", "CLINICIAN_REVIEW"].includes(r.status);
  const quotes = c.criteria.filter((x) => x.quote).map((x) => x.quote as string);
  const left = hoursLeft(r.sla_due_at);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/payer" className="text-sm text-accent hover:underline">
            Work queue
          </Link>
          <h1 className="mt-1 font-serif text-3xl font-semibold tracking-tight">
            {r.pa_id} · {r.service_display}
          </h1>
          <p className="text-sm text-ink-soft">
            Member {r.member_id} · {r.line_of_business} · ordering NPI {r.ordering_npi} · {r.priority} · policy {r.policy_doc_id} · version {r.version ?? 1}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <StatusPill status={r.status} />
          {open && <span className={`text-xs ${left < 24 ? "font-semibold text-deny" : "text-ink-soft"}`}>Decision due in {formatHours(left)}</span>}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <div className="space-y-6">
          <Section title="Criteria and evidence" aside={<StatusPill status={r.recommendation} />}>
            <p className="mb-4 text-sm text-ink-soft">{r.reason_text}</p>
            <CriteriaTree criteria={c.criteria} canEdit={open} onOverride={override} />
            {c.ai_cross_check && c.ai_cross_check.length > 0 && (
              <div className="mt-5 border-t border-rule pt-3 text-sm">
                <div className="mb-1 font-semibold">Independent AI read of the submitted records</div>
                <ul className="space-y-1">
                  {c.ai_cross_check.map((x) => (
                    <li key={x.fact_name} className={x.agrees === false ? "text-deny" : "text-ink-soft"}>
                      {x.fact_name}: clinic said {String(x.provider_value)}, AI found {String(x.ai_value)}
                      {x.agrees === false ? " – check this" : ""}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Section>

          <Section title="Submitted records">
            <div className="space-y-5">
              {c.documents.length === 0 && <p className="text-sm text-ink-soft">No documents were attached.</p>}
              {c.documents.map((d) => (
                <article key={d.doc_id}>
                  <header className="text-sm">
                    <span className="font-semibold">{d.title ?? d.doc_id}</span> <span className="text-ink-soft">{d.encounter_date}</span>
                  </header>
                  <p className="doc-text mt-1">
                    <Highlighted text={d.text} quotes={quotes} />
                  </p>
                </article>
              ))}
            </div>
          </Section>

          <details className="panel">
            <summary className="cursor-pointer px-4 py-2.5 text-sm font-semibold">Policy {r.policy_doc_id}</summary>
            <div className="space-y-3 border-t border-rule p-4 text-sm">
              {c.policy_sections.map((s) => (
                <div key={s.section_title}>
                  <div className="font-semibold">{s.section_title}</div>
                  <p className="doc-text text-ink-soft">{s.text}</p>
                </div>
              ))}
            </div>
          </details>
        </div>

        <div className="space-y-6">
          <Section title="Decision">
            {open ? (
              <div className="space-y-3">
                <label className="block">
                  <span className="field-label">Reviewing as</span>
                  <select className="field" value={reviewer.id} onChange={(e) => setReviewer(REVIEWERS.find((x) => x.id === e.target.value)!)}>
                    {REVIEWERS.map((x) => (
                      <option key={x.id} value={x.id}>
                        {x.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <span className="field-label">Reason or request to the clinic</span>
                  <textarea
                    className="field"
                    rows={3}
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Name the criterion and what would satisfy it"
                  />
                </label>
                <div className="flex flex-wrap gap-2">
                  <button className="btn-primary" disabled={busy} onClick={() => decide("APPROVE")}>
                    Approve
                  </button>
                  <button className="btn-quiet" disabled={busy || !reason.trim()} onClick={() => decide("PEND")}>
                    Request more information
                  </button>
                  <button
                    className="btn-danger"
                    disabled={busy || reviewer.role !== "MEDICAL_DIRECTOR" || !reason.trim()}
                    onClick={() => decide("DENY")}
                    title={reviewer.role !== "MEDICAL_DIRECTOR" ? "Only a medical director can deny" : undefined}
                  >
                    Deny
                  </button>
                </div>
                {reviewer.role !== "MEDICAL_DIRECTOR" && <p className="text-xs text-ink-soft">Only a medical director can deny. Nurses approve or request information.</p>}
                <ErrorNote error={error} />
              </div>
            ) : (
              <p className="text-sm">This request is {r.status.toLowerCase()}. The clinic was notified.</p>
            )}
            <ol className="mt-4 space-y-2 border-t border-rule pt-3 text-xs">
              {c.decisions.map((d, i) => (
                <li key={i} className="flex gap-2">
                  <StatusPill status={d.review_action_code} />
                  <span className="text-ink-soft">
                    {d.decided_by === "SYSTEM" ? "AuthBridge engine" : d.decided_by} · {new Date(d.decided_at + (d.decided_at.endsWith("Z") ? "" : "Z")).toLocaleString()}
                    {d.reason_text ? ` — ${d.reason_text}` : ""}
                  </span>
                </li>
              ))}
            </ol>
          </Section>

          {r.status === "DENIED" && (
            <Section title="Denial letter">
              <button className="btn-quiet" onClick={() => get<string>(payer(`/internal/cases/${id}/letter`)).then(setLetter).catch((e) => setError(e.message))}>
                Show letter
              </button>
              {letter && <pre className="doc-text mt-3 whitespace-pre-wrap text-sm">{letter}</pre>}
            </Section>
          )}

          <Section title="Ask about this case">
            <AgentChat
              agent="clinical_review"
              paId={r.pa_id}
              placeholder="Ask the review agent"
              suggestions={["Summarize why this was flagged", "What documentation would resolve it?"]}
            />
          </Section>

          <Section title="Audit trail">
            <ul className="space-y-1 text-xs text-ink-soft">
              {c.audit.map((a, i) => (
                <li key={i}>
                  {a.created_at?.replace("T", " ").slice(0, 19)} · {a.agent_name}
                  {a.human_actor ? ` (${a.human_actor})` : ""} · {a.recommendation ?? ""}
                </li>
              ))}
            </ul>
          </Section>
        </div>
      </div>
    </div>
  );
}
