import type { Order } from "@/lib/types";

type StepState = "done" | "current" | "skipped" | "todo" | "ok" | "pend" | "deny";

const DOT: Record<StepState, string> = {
  done: "bg-accent border-accent",
  current: "bg-paper border-accent ring-4 ring-accent-soft",
  skipped: "bg-paper border-rule",
  todo: "bg-paper border-rule",
  ok: "bg-ok border-ok",
  pend: "bg-pend border-pend",
  deny: "bg-deny border-deny",
};

/** The order's path through CRD → DTR → PAS, as a horizontal track. */
export function JourneyTrack({ order }: { order: Order }) {
  const info = order.crd?.coverage_information;
  const shortCircuit = ["NO_AUTH_NEEDED", "GOLD_CARD", "NOT_COVERED"].includes(order.status);
  const action = order.pas?.review_action;
  const steps: { label: string; detail: string; state: StepState }[] = [
    { label: "Signed", detail: order.status === "DRAFT" ? "Draft saved" : "Order signed", state: order.status === "DRAFT" ? "current" : "done" },
    {
      label: "Coverage check",
      detail: !info
        ? "Waiting for signature"
        : info.covered === "not-covered"
          ? "Not covered"
          : info.pa_needed === "no-auth"
            ? "No prior auth needed"
            : info.pa_needed === "satisfied"
              ? `Gold card · ${info.satisfied_pa_id}`
              : "Prior auth needed",
      state: !info ? "todo" : shortCircuit ? (order.status === "NOT_COVERED" ? "deny" : "ok") : "done",
    },
    {
      label: "Documentation",
      detail: shortCircuit ? "Not needed" : order.dtr ? `${Object.keys(order.dtr.answers || {}).length} answers` : "Not started",
      state: shortCircuit ? "skipped" : order.pas ? "done" : order.dtr || order.status === "DOC_NEEDED" ? "current" : "todo",
    },
    {
      label: "Submitted",
      detail: order.pas ? `Request ${order.pas.pa_id}` : shortCircuit ? "Not needed" : "Not yet",
      state: shortCircuit ? "skipped" : order.pas ? "done" : "todo",
    },
    {
      label: "Decision",
      detail: action ? `${action} ${order.pas?.review_action_display ?? ""}` : shortCircuit ? "Complete at signing" : "Pending",
      state: action === "A1" || action === "A6" ? "ok" : action === "A4" ? "pend" : action === "A3" ? "deny" : shortCircuit ? "skipped" : "todo",
    },
  ];
  return (
    <ol className="grid grid-cols-1 gap-3 sm:grid-cols-5 sm:gap-0" aria-label="Order progress">
      {steps.map((s, i) => (
        <li key={s.label} className="relative flex gap-3 sm:flex-col sm:gap-2 sm:pr-4">
          {i < steps.length - 1 && (
            <span className="absolute left-[7px] top-5 h-[calc(100%+0.25rem)] w-px bg-rule sm:left-4 sm:top-[7px] sm:h-px sm:w-full" aria-hidden />
          )}
          <span className={`relative z-10 mt-0.5 h-4 w-4 shrink-0 rounded-full border-2 ${DOT[s.state]}`} aria-hidden />
          <span>
            <span className={`block text-sm font-semibold ${s.state === "skipped" || s.state === "todo" ? "text-ink-soft" : "text-ink"}`}>{s.label}</span>
            <span className="block text-xs text-ink-soft">{s.detail}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}
