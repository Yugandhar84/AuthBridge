"use client";

import { useState } from "react";
import { payer, streamAgent } from "@/lib/api";

type Msg = { role: "user" | "agent"; text: string; status?: string; table?: { columns?: string[]; rows?: unknown[][] }; error?: string };

/** Streams answers from a Cortex Agent (via the payer service). */
export function AgentChat({
  agent,
  paId,
  placeholder,
  suggestions = [],
}: {
  agent: "analytics" | "clinical_review" | "denial_appeal";
  paId?: string;
  placeholder: string;
  suggestions?: string[];
}) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  async function ask(question: string) {
    if (!question.trim() || busy) return;
    setBusy(true);
    setInput("");
    setMessages((m) => [...m, { role: "user", text: question }, { role: "agent", text: "" }]);
    const update = (fn: (m: Msg) => Msg) => setMessages((all) => [...all.slice(0, -1), fn(all[all.length - 1])]);
    try {
      for await (const ev of streamAgent(payer(`/internal/agents/${agent}/run`), { message: question, pa_id: paId })) {
        if (ev.type === "text") update((m) => ({ ...m, text: m.text + ev.text, status: undefined }));
        else if (ev.type === "status") update((m) => ({ ...m, status: ev.message }));
        else if (ev.type === "table") update((m) => ({ ...m, table: ev.result_set as Msg["table"] }));
        else if (ev.type === "error") update((m) => ({ ...m, error: ev.message }));
      }
    } catch (e) {
      update((m) => ({ ...m, error: (e as Error).message }));
    } finally {
      update((m) => ({ ...m, status: undefined }));
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="space-y-3" aria-live="polite">
        {messages.map((m, i) =>
          m.role === "user" ? (
            <p key={i} className="ml-auto max-w-[85%] rounded-lg bg-accent-soft px-3 py-2 text-sm">
              {m.text}
            </p>
          ) : (
            <div key={i} className="max-w-[95%] text-sm">
              {m.status && <p className="text-xs text-ink-soft">{m.status}…</p>}
              {m.text && <p className="whitespace-pre-wrap leading-relaxed">{m.text}</p>}
              {m.table?.columns && m.table.rows && (
                <div className="mt-2 overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-rule">
                        {m.table.columns.map((c) => (
                          <th key={c} className="py-1 pr-3 font-semibold">
                            {c}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {m.table.rows.map((r, j) => (
                        <tr key={j} className="border-b border-rule last:border-0">
                          {r.map((v, k) => (
                            <td key={k} className="py-1 pr-3 tabular-nums">
                              {String(v)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {m.error && <p className="text-deny">{m.error}</p>}
            </div>
          ),
        )}
      </div>
      {messages.length === 0 && suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {suggestions.map((s) => (
            <button key={s} className="rounded-full border border-rule px-3 py-1 text-xs hover:border-accent" onClick={() => ask(s)}>
              {s}
            </button>
          ))}
        </div>
      )}
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
      >
        <input className="field" value={input} onChange={(e) => setInput(e.target.value)} placeholder={placeholder} aria-label={placeholder} />
        <button className="btn-primary" disabled={busy || !input.trim()}>
          {busy ? "Thinking…" : "Ask"}
        </button>
      </form>
    </div>
  );
}
