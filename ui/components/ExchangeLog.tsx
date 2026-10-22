"use client";

import { useState } from "react";
import { JsonBlock } from "./ui";
import type { Exchange } from "@/lib/types";

const NAMES: Record<string, string> = {
  "order-select": "CDS Hooks order-select (CRD)",
  "order-sign": "CDS Hooks order-sign (CRD)",
  "$questionnaire-package": "Questionnaire/$questionnaire-package (DTR)",
  "Claim/$submit": "Claim/$submit (PAS)",
  notification: "Subscription notification (PAS)",
};

/** Developer view of every standards message for this order. */
export function ExchangeLog({ exchanges }: { exchanges: Exchange[] }) {
  const [open, setOpen] = useState<number | null>(null);
  return (
    <details className="panel">
      <summary className="cursor-pointer px-4 py-2.5 text-sm font-semibold">
        FHIR messages for this order ({exchanges.length})
      </summary>
      <ul className="divide-y divide-rule border-t border-rule">
        {exchanges.map((x, i) => (
          <li key={i} className="px-4 py-2">
            <button className="flex w-full items-center justify-between gap-3 text-left text-sm" onClick={() => setOpen(open === i ? null : i)} aria-expanded={open === i}>
              <span>
                <span className="font-medium">{NAMES[x.endpoint] ?? x.endpoint}</span>
                <span className="ml-2 text-xs text-ink-soft">{new Date(x.at).toLocaleTimeString()}</span>
              </span>
              <span className="text-xs text-ink-soft">
                HTTP {x.status}
                {x.ms !== undefined ? ` · ${x.ms} ms` : ""}
              </span>
            </button>
            {open === i && (
              <div className="mt-2 grid gap-3 lg:grid-cols-2">
                <div>
                  <div className="mb-1 text-xs font-semibold text-ink-soft">{x.endpoint === "notification" ? "Received" : "Sent"}</div>
                  <JsonBlock value={x.request} />
                </div>
                <div>
                  <div className="mb-1 text-xs font-semibold text-ink-soft">Response</div>
                  <JsonBlock value={x.response} />
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>
    </details>
  );
}
