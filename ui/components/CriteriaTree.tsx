"use client";

import type { Criterion } from "@/lib/types";
import { display } from "@/lib/status";

const MARK: Record<string, { sym: string; cls: string; word: string }> = {
  MET: { sym: "✓", cls: "border-ok text-ok", word: "Met" },
  NOT_MET: { sym: "✕", cls: "border-deny text-deny", word: "Not met" },
  UNKNOWN: { sym: "?", cls: "border-pend text-pend", word: "Unknown" },
};

function threshold(c: Criterion) {
  if (c.operator === "=" && typeof c.threshold === "boolean") return c.threshold ? "must be yes" : "must be no";
  return `must be ${c.operator} ${String(c.threshold)}`;
}

/** The policy as a logic tree: each branch says whether ALL or ANY of its
 *  children must hold, so reviewers can see exactly why the engine reached
 *  its recommendation. */
export function CriteriaTree({
  criteria,
  onOverride,
  canEdit,
}: {
  criteria: Criterion[];
  onOverride?: (c: Criterion, status: string) => void;
  canEdit?: boolean;
}) {
  const children = (id: string | null) => criteria.filter((c) => c.parent_node_id === id);
  const root = children(null)[0];
  if (!root) return <p className="text-sm text-ink-soft">No criteria apply to this service.</p>;

  const render = (node: Criterion): React.ReactNode => {
    const m = MARK[node.reviewer_override || node.status] ?? MARK.UNKNOWN;
    if (node.node_type !== "LEAF") {
      return (
        <li key={node.node_id} className="relative">
          <div className="flex items-center gap-2 py-1">
            <span className={`grid h-6 min-w-6 place-items-center rounded border px-1 text-xs font-bold ${m.cls}`} aria-label={m.word}>
              {m.sym}
            </span>
            <span className="text-sm font-semibold">{node.label}</span>
            <span className="rounded bg-wash px-1.5 py-0.5 text-[11px] font-semibold text-ink-soft">
              {node.node_type === "AND" ? "all of" : "any of"}
            </span>
            <span className="text-xs text-ink-soft">§ {node.policy_section_id}</span>
          </div>
          <ul className="ml-3 border-l-2 border-dashed border-rule pl-5">{children(node.node_id).map(render)}</ul>
        </li>
      );
    }
    return (
      <li key={node.node_id} className="relative py-2 before:absolute before:-left-5 before:top-5 before:h-px before:w-4 before:bg-rule">
        <div className="flex flex-wrap items-start gap-x-3 gap-y-1">
          <span className={`mt-0.5 grid h-6 min-w-6 place-items-center rounded border px-1 text-xs font-bold ${m.cls}`} aria-label={m.word}>
            {m.sym}
          </span>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-medium">
              {node.label} <span className="text-xs font-normal text-ink-soft">§ {node.policy_section_id}</span>
            </div>
            <div className="text-sm text-ink-soft">
              Documented: <span className="font-semibold text-ink">{display(node.value)}</span> · {threshold(node)}
              {node.origin ? ` · answer ${node.origin === "auto" ? "filled from chart" : node.origin === "override" ? "edited by clinician" : "entered by clinician"}` : ""}
            </div>
            {node.quote ? (
              <p className="mt-1 border-l-2 border-rule pl-3 font-serif text-sm">
                “{node.quote}”{" "}
                <span className={`font-sans text-xs ${node.citation_verified ? "text-ok" : "text-deny"}`}>
                  {node.citation_verified ? `verified in ${node.doc_id}` : `not found in ${node.doc_id ?? "submitted records"}`}
                </span>
              </p>
            ) : (
              <p className="mt-1 text-xs text-pend">No supporting quote submitted.</p>
            )}
            {node.reviewer_override && (
              <p className="mt-1 text-xs text-review">
                Reviewer set this to {MARK[node.reviewer_override]?.word.toLowerCase()}: {node.override_reason}
              </p>
            )}
          </div>
          {canEdit && onOverride && (
            <select
              className="field w-40 py-1 text-xs"
              aria-label={`Reviewer finding for ${node.label}`}
              value={node.reviewer_override ?? ""}
              onChange={(e) => e.target.value && onOverride(node, e.target.value)}
            >
              <option value="">Engine finding</option>
              <option value="MET">Set to met</option>
              <option value="NOT_MET">Set to not met</option>
              <option value="UNKNOWN">Set to unknown</option>
            </select>
          )}
        </div>
      </li>
    );
  };

  return <ul>{render(root)}</ul>;
}
