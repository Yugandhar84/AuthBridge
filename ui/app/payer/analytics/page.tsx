"use client";

import { useEffect, useState } from "react";
import { AgentChat } from "@/components/AgentChat";
import { ErrorNote, Section, StatusPill } from "@/components/ui";
import { get, payer } from "@/lib/api";
import { formatHours, pct } from "@/lib/status";
import type { Metrics } from "@/lib/types";

export default function Analytics() {
  const [m, setM] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    get<Metrics>(payer("/internal/metrics")).then(setM).catch((e) => setError(e.message));
  }, []);

  const figures: [string, string, string][] = m
    ? [
        ["Decided within the deadline", pct(m.sla_compliance), "72 hours urgent, 7 days standard"],
        ["Approved in real time", pct(m.auto_approval_rate), "no human touch, evidence verified"],
        ["Median time to decision", formatHours(m.median_hours_to_decision), `standard ${formatHours(m.median_hours_standard)} · urgent ${formatHours(m.median_hours_expedited)}`],
        ["Denials overturned on appeal", pct(m.appeal_overturn_rate), "watch this; high means weak denials"],
      ]
    : [];
  const max = Math.max(1, ...(m?.by_service.map((s) => s.requests) ?? [1]));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-3xl font-semibold tracking-tight">Prior authorization metrics</h1>
        <p className="text-sm text-ink-soft">
          {m ? `${m.total_requests} requests, ${m.decided} decided. ` : ""}Synthetic data. Check the CMS-0057-F metric definitions before public reporting.
        </p>
      </div>
      <ErrorNote error={error} />

      <dl className="grid gap-px overflow-hidden rounded-lg border border-rule bg-rule sm:grid-cols-2 lg:grid-cols-4">
        {figures.map(([label, value, sub]) => (
          <div key={label} className="bg-paper p-4">
            <dt className="text-sm text-ink-soft">{label}</dt>
            <dd className="mt-1 font-serif text-3xl font-semibold tabular-nums">{value}</dd>
            <dd className="text-xs text-ink-soft">{sub}</dd>
          </div>
        ))}
      </dl>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <div className="space-y-6">
          <Section title="Outcomes by service">
            <ul className="space-y-3">
              {m?.by_service.map((s) => (
                <li key={s.service_code}>
                  <div className="flex justify-between text-sm">
                    <span>{s.service_display}</span>
                    <span className="tabular-nums text-ink-soft">{s.requests}</span>
                  </div>
                  <div className="mt-1 flex h-2.5 overflow-hidden rounded-sm bg-wash" style={{ width: `${(s.requests / max) * 100}%` }} aria-hidden>
                    <span className="bg-ok" style={{ width: `${(s.auto_approved / s.requests) * 100}%` }} />
                    <span className="bg-ok opacity-50" style={{ width: `${((s.approved - s.auto_approved) / s.requests) * 100}%` }} />
                    <span className="bg-deny" style={{ width: `${(s.denied / s.requests) * 100}%` }} />
                  </div>
                  <div className="mt-0.5 text-xs text-ink-soft">
                    {s.auto_approved} approved in real time · {s.approved - s.auto_approved} approved after review · {s.denied} denied
                  </div>
                </li>
              ))}
            </ul>
          </Section>
          <Section title="Gold card status">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-rule text-xs text-ink-soft">
                  <th className="py-1.5 font-semibold">Ordering NPI</th>
                  <th className="py-1.5 font-semibold">Service</th>
                  <th className="py-1.5 font-semibold">Approval rate</th>
                  <th className="py-1.5 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody>
                {m?.gold_card.map((g) => (
                  <tr key={g.ordering_npi + g.service_code} className="border-b border-rule last:border-0">
                    <td className="py-2 tabular-nums">{g.ordering_npi}</td>
                    <td className="py-2">{g.service_code}</td>
                    <td className="py-2 tabular-nums">{pct(g.approval_rate)}</td>
                    <td className="py-2">
                      <StatusPill status={g.status === "GOLD" ? "GOLD_CARD" : "PENDED"} label={g.status === "GOLD" ? "Gold card" : g.status === "NEAR" ? "Near gold" : "None"} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
        </div>
        <Section title="Ask the analytics agent">
          <AgentChat
            agent="analytics"
            placeholder="Ask about volumes, deadlines or approval rates"
            suggestions={[
              "Which services have the highest auto-approval rate?",
              "What share of urgent requests met the 72-hour limit?",
              "Which practitioners are close to gold card for lumbar MRI?",
            ]}
          />
        </Section>
      </div>
    </div>
  );
}
