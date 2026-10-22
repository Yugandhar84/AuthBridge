"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ErrorNote, StatusPill } from "@/components/ui";
import { get, payer } from "@/lib/api";
import { formatHours, hoursLeft } from "@/lib/status";
import type { QueueRow } from "@/lib/types";

const FILTERS = [
  ["open", "Needs a person"],
  ["all", "All live requests"],
] as const;

export default function WorkQueue() {
  const [rows, setRows] = useState<QueueRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<(typeof FILTERS)[number][0]>("open");

  useEffect(() => {
    const load = () => get<QueueRow[]>(payer("/internal/queue")).then(setRows).catch((e) => setError(e.message));
    load();
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  }, []);

  const shown = (rows ?? []).filter((r) => filter === "all" || ["PENDED", "CLINICIAN_REVIEW"].includes(r.status));

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-serif text-3xl font-semibold tracking-tight">Prior authorization work queue</h1>
          <p className="text-sm text-ink-soft">Sorted by time left before the CMS-0057-F decision deadline (72 hours urgent, 7 days standard).</p>
        </div>
        <div className="flex rounded-md border border-rule p-0.5 text-sm" role="tablist">
          {FILTERS.map(([k, l]) => (
            <button key={k} role="tab" aria-selected={filter === k} onClick={() => setFilter(k)} className={`rounded px-3 py-1 ${filter === k ? "bg-wash font-semibold" : "text-ink-soft"}`}>
              {l}
            </button>
          ))}
        </div>
      </div>
      <ErrorNote error={error && `Could not load the queue: ${error}`} />
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead>
            <tr className="border-b border-rule text-xs text-ink-soft">
              <th className="py-2 pr-4 font-semibold">Time left</th>
              <th className="py-2 pr-4 font-semibold">Request</th>
              <th className="py-2 pr-4 font-semibold">Service</th>
              <th className="py-2 pr-4 font-semibold">Engine recommendation</th>
              <th className="py-2 pr-4 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => {
              const left = hoursLeft(r.sla_due_at);
              const done = ["APPROVED", "DENIED"].includes(r.status);
              return (
                <tr key={r.pa_id} className="border-b border-rule hover:bg-wash">
                  <td className={`py-3 pr-4 tabular-nums ${done ? "text-ink-soft" : left < 24 ? "font-semibold text-deny" : ""}`}>
                    {done ? "Decided" : left < 0 ? `Overdue ${formatHours(-left)}` : formatHours(left)}
                    {r.priority === "expedited" && <span className="ml-2 text-xs font-semibold text-deny">urgent</span>}
                  </td>
                  <td className="py-3 pr-4">
                    <Link href={`/payer/cases/${r.pa_id}`} className="font-semibold text-accent hover:underline">
                      {r.pa_id}
                    </Link>
                    <div className="text-xs text-ink-soft">
                      Member {r.member_id} · {r.line_of_business} · NPI {r.ordering_npi}
                    </div>
                  </td>
                  <td className="py-3 pr-4">
                    {r.service_display}
                    <div className="text-xs text-ink-soft">{r.service_code}</div>
                  </td>
                  <td className="py-3 pr-4">
                    <StatusPill status={r.recommendation} />
                  </td>
                  <td className="py-3 pr-4">
                    <StatusPill status={r.status} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {rows && shown.length === 0 && (
          <p className="py-8 text-center text-sm text-ink-soft">
            Nothing needs a reviewer. Submit a request from the Clinic side (try the home oxygen patient) to see one here.
          </p>
        )}
      </div>
    </div>
  );
}
