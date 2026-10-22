"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ExchangeLog } from "@/components/ExchangeLog";
import { JourneyTrack } from "@/components/JourneyTrack";
import { ErrorNote, Highlighted, Section, StatusPill } from "@/components/ui";
import { get, provider, send } from "@/lib/api";
import { display } from "@/lib/status";
import type { Answer, Note, Order, QItem } from "@/lib/types";

type Docs = { documents: Note[]; attachable: { doc_id: string; title: string; note_type: string; encounter_date: string }[] };

const ORIGIN_LABEL: Record<string, string> = { auto: "From chart", override: "Edited by you", manual: "Entered by you" };

export default function OrderWorkspace() {
  const { id } = useParams<{ id: string }>();
  const [order, setOrder] = useState<Order | null>(null);
  const [docs, setDocs] = useState<Docs | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [focus, setFocus] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [o, d] = await Promise.all([get<Order>(provider(`/api/orders/${id}`)), get<Docs>(provider(`/api/orders/${id}/documents`))]);
    setOrder(o);
    setDocs(d);
  }, [id]);

  useEffect(() => {
    refresh().catch((e) => setError(e.message));
  }, [refresh]);

  // Pended requests are finished by a Subscription notification; poll as a fallback.
  useEffect(() => {
    if (order?.status !== "PENDED") return;
    const t = setInterval(() => refresh().catch(() => undefined), 5000);
    return () => clearInterval(t);
  }, [order?.status, refresh]);

  async function act(label: string, fn: () => Promise<Order>) {
    setBusy(label);
    setError(null);
    try {
      setOrder(await fn());
      setDocs(await get<Docs>(provider(`/api/orders/${id}/documents`)));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  if (!order) return <ErrorNote error={error} />;
  const info = order.crd?.coverage_information;
  const dtr = order.dtr;
  const pas = order.pas;
  const quotes = Object.values(dtr?.answers ?? {}).filter((a) => a.quote).map((a) => a.quote as string);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href={`/provider/patients/${order.patient_id}`} className="text-sm text-accent hover:underline">
            Back to chart
          </Link>
          <h1 className="mt-1 font-serif text-3xl font-semibold tracking-tight">{order.display}</h1>
          <p className="text-sm text-ink-soft">
            Order {order.order_id} · {order.code}
          </p>
        </div>
        <StatusPill status={order.status} />
      </div>

      <div className="panel p-4">
        <JourneyTrack order={order} />
      </div>

      <ErrorNote error={error} />

      {order.status === "DRAFT" && (
        <button className="btn-primary" disabled={!!busy} onClick={() => act("sign", () => send<Order>(provider(`/api/orders/${id}/sign`)))}>
          {busy ? "Checking coverage…" : "Sign order"}
        </button>
      )}

      {info && (
        <Section title="Coverage from Demo Health Plan">
          <CoverageSummary order={order} />
          {order.crd?.cards?.map((c, i) => (
            <div key={i} className="mt-3 rounded-md border-l-4 border-accent bg-wash px-3 py-2 text-sm">
              <div className="font-medium">{c.summary}</div>
              {c.detail && <div className="text-ink-soft">{c.detail}</div>}
              {c.links?.map((l) => (
                <a key={l.url} href={l.url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-accent hover:underline">
                  {l.label}
                </a>
              ))}
            </div>
          ))}
          {order.status === "DOC_NEEDED" && !dtr && (
            <button className="btn-primary mt-4" disabled={!!busy} onClick={() => act("dtr", () => send<Order>(provider(`/api/orders/${id}/dtr`)))}>
              {busy === "dtr" ? "Filling from the chart…" : "Complete documentation"}
            </button>
          )}
        </Section>
      )}

      {dtr && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
          <Section title={dtr.questionnaire.title}>
            <Questionnaire
              items={dtr.questionnaire.item}
              prefilled={dtr.prefilled}
              answers={dtr.answers}
              locked={!!pas && pas.review_action !== "A4"}
              onFocus={setFocus}
              onChange={(linkId, value) =>
                act("answers", () => send<Order>(provider(`/api/orders/${id}/answers`), { answers: { [linkId]: value } }, "PUT"))
              }
            />
            {dtr.completeness && <Completeness c={dtr.completeness} />}
            {(!pas || pas.review_action === "A4") && (
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <button className="btn-primary" disabled={!!busy} onClick={() => act("submit", () => send<Order>(provider(`/api/orders/${id}/submit`)))}>
                  {busy === "submit" ? "Submitting…" : pas ? "Resubmit to plan" : "Submit prior authorization"}
                </button>
                <span className="text-xs text-ink-soft">You are confirming these answers. AI-filled answers are marked “From chart”.</span>
              </div>
            )}
          </Section>
          <Section title="Evidence from the chart">
            <div className="space-y-5">
              {docs?.documents.map((n) => {
                const cited = Object.values(dtr.answers).some((a) => a.doc_id === n.doc_id);
                return (
                  <article key={n.doc_id} className={focus && dtr.answers[focus]?.doc_id === n.doc_id ? "rounded-md ring-2 ring-accent ring-offset-4 ring-offset-paper" : ""}>
                    <header className="flex flex-wrap items-baseline gap-x-3 text-sm">
                      <span className="font-semibold">{n.title}</span>
                      <span className="text-ink-soft">
                        {n.note_type} · {n.encounter_date}
                        {cited ? " · cited" : ""}
                      </span>
                    </header>
                    <p className="doc-text mt-1">
                      <Highlighted text={n.text} quotes={quotes} />
                    </p>
                  </article>
                );
              })}
            </div>
          </Section>
        </div>
      )}

      {pas && <Decision order={order} docs={docs} busy={busy} act={act} />}

      {order.exchanges && order.exchanges.length > 0 && <ExchangeLog exchanges={order.exchanges} />}
    </div>
  );
}

function CoverageSummary({ order }: { order: Order }) {
  const info = order.crd!.coverage_information!;
  const rows: [string, string][] = [
    ["Covered", info.covered === "covered" ? "Yes" : info.covered === "not-covered" ? "No" : "Conditional"],
    [
      "Prior authorization",
      info.pa_needed === "no-auth"
        ? "Not needed"
        : info.pa_needed === "satisfied"
          ? `Already satisfied (${info.satisfied_pa_id})`
          : info.pa_needed === "auth-needed"
            ? "Needed"
            : info.pa_needed ?? "–",
    ],
  ];
  if (info.doc_needed) rows.push(["Documentation", info.doc_needed === "clinical" ? "Clinical questionnaire" : info.doc_needed]);
  if (info.reason_text) rows.push(["Note", info.reason_text]);
  rows.push(["Coverage assertion", info.coverage_assertion_id ?? "–"]);
  return (
    <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[12rem_1fr]">
      {rows.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-ink-soft">{k}</dt>
          <dd className="font-medium">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

function Questionnaire({
  items,
  prefilled,
  answers,
  locked,
  onChange,
  onFocus,
}: {
  items: QItem[];
  prefilled: Record<string, unknown>;
  answers: Record<string, Answer>;
  locked: boolean;
  onChange: (linkId: string, value: unknown) => void;
  onFocus: (linkId: string | null) => void;
}) {
  return (
    <div className="space-y-6">
      {items.map((g) =>
        g.type === "group" ? (
          <fieldset key={g.linkId}>
            <legend className="mb-2 text-xs font-semibold text-ink-soft">{g.text}</legend>
            <div className="space-y-4">
              {g.item?.map((it) =>
                it.readOnly ? (
                  <div key={it.linkId} className="flex justify-between gap-4 text-sm">
                    <span className="text-ink-soft">{it.text}</span>
                    <span className="font-medium">{display(prefilled[it.linkId])}</span>
                  </div>
                ) : (
                  <QuestionRow key={it.linkId} item={it} answer={answers[it.linkId]} locked={locked} onChange={onChange} onFocus={onFocus} />
                ),
              )}
            </div>
          </fieldset>
        ) : null,
      )}
    </div>
  );
}

function QuestionRow({
  item,
  answer,
  locked,
  onChange,
  onFocus,
}: {
  item: QItem;
  answer?: Answer;
  locked: boolean;
  onChange: (linkId: string, value: unknown) => void;
  onFocus: (linkId: string | null) => void;
}) {
  const [draft, setDraft] = useState(answer?.value === undefined ? "" : String(answer.value));
  useEffect(() => setDraft(answer?.value === undefined ? "" : String(answer.value)), [answer?.value]);
  const id = `q-${item.linkId}`;
  return (
    <div className="rounded-md border border-rule p-3" onMouseEnter={() => onFocus(item.linkId)} onMouseLeave={() => onFocus(null)}>
      <label htmlFor={id} className="block text-sm font-medium">
        {item.text}
      </label>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        {item.type === "boolean" ? (
          <div className="flex gap-2" role="radiogroup" aria-labelledby={id}>
            {[true, false].map((v) => (
              <button
                key={String(v)}
                type="button"
                id={v ? id : undefined}
                role="radio"
                aria-checked={answer?.value === v}
                disabled={locked}
                onClick={() => onChange(item.linkId, v)}
                className={`rounded-md border px-3 py-1 text-sm ${answer?.value === v ? "border-accent bg-accent-soft font-semibold text-accent" : "border-rule"}`}
              >
                {v ? "Yes" : "No"}
              </button>
            ))}
          </div>
        ) : (
          <input
            id={id}
            className="field max-w-40"
            type={item.type === "integer" || item.type === "decimal" ? "number" : "text"}
            step={item.type === "decimal" ? "0.1" : "1"}
            value={draft}
            disabled={locked}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={() => draft !== (answer?.value === undefined ? "" : String(answer.value)) && onChange(item.linkId, draft === "" ? null : Number(draft))}
          />
        )}
        {answer ? (
          <span className={`text-xs ${answer.origin === "auto" ? "text-accent" : "text-ink-soft"}`}>
            {ORIGIN_LABEL[answer.origin]}
            {answer.origin === "auto" && answer.confidence ? ` · ${answer.confidence} confidence` : ""}
          </span>
        ) : (
          <span className="text-xs text-pend">Not found in the chart</span>
        )}
      </div>
      {answer?.quote && (
        <p className="mt-2 border-l-2 border-rule pl-3 font-serif text-sm text-ink-soft">
          “{answer.quote}” <span className="font-sans text-xs">— {answer.doc_title ?? answer.doc_id}</span>
        </p>
      )}
      {answer?.origin === "override" && <p className="mt-2 text-xs text-pend">The chart quote no longer supports this value, so the plan will ask for documentation.</p>}
    </div>
  );
}

function Completeness({ c }: { c: NonNullable<Order["dtr"]>["completeness"] }) {
  if (!c) return null;
  const tone = c.recommendation === "AUTO_APPROVE" ? "border-ok text-ok" : c.recommendation === "PEND" ? "border-pend text-pend" : "border-review text-review";
  const headline =
    c.recommendation === "AUTO_APPROVE"
      ? "Meets the plan's criteria with chart evidence. Likely approved on submission."
      : c.recommendation === "PEND"
        ? "Likely to be pended. Add the documentation below before submitting if you have it."
        : "As documented, this does not meet the plan's criteria. A plan clinician will review it.";
  return (
    <div className={`mt-5 rounded-md border-l-4 bg-wash px-3 py-2 text-sm ${tone}`}>
      <div className="font-semibold">{headline}</div>
      <ul className="mt-1 list-disc pl-5 text-ink">
        {(c.missing_info.length ? c.missing_info : c.unmet).map((m) => (
          <li key={m}>{m}</li>
        ))}
      </ul>
    </div>
  );
}

function Decision({
  order,
  docs,
  busy,
  act,
}: {
  order: Order;
  docs: Docs | null;
  busy: string | null;
  act: (label: string, fn: () => Promise<Order>) => void;
}) {
  const pas = order.pas!;
  const id = order.order_id;
  return (
    <Section title="Decision from Demo Health Plan" aside={<StatusPill status={pas.review_action} />}>
      {pas.review_action === "A1" || pas.review_action === "A6" ? (
        <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[12rem_1fr]">
          <dt className="text-ink-soft">Authorization number</dt>
          <dd className="font-serif text-lg font-semibold">{pas.auth_number}</dd>
          <dt className="text-ink-soft">Valid</dt>
          <dd>
            {pas.period?.start} to {pas.period?.end}
          </dd>
          <dt className="text-ink-soft">Reason</dt>
          <dd>{pas.reason_text}</dd>
        </dl>
      ) : pas.review_action === "A4" ? (
        <div className="space-y-3 text-sm">
          <p>{pas.reason_text}</p>
          {pas.request_text && (
            <p className="rounded-md border-l-4 border-pend bg-wash px-3 py-2">
              <span className="font-semibold">The plan asks for: </span>
              {pas.request_text}
            </p>
          )}
          <p className="text-xs text-ink-soft">Reference {pas.admin_ref}. This page updates when the plan decides.</p>
          {docs && docs.attachable.length > 0 && (
            <div>
              <div className="mb-1 font-medium">Attach a document</div>
              <ul className="space-y-2">
                {docs.attachable.map((d) => (
                  <li key={d.doc_id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-rule px-3 py-2">
                    <span>
                      {d.title} <span className="text-ink-soft">({d.note_type}, {d.encounter_date})</span>
                    </span>
                    <button
                      className="btn-quiet"
                      disabled={!!busy}
                      onClick={() => act("attach", () => send<Order>(provider(`/api/orders/${id}/attach`), { doc_id: d.doc_id }))}
                    >
                      {busy === "attach" ? "Attaching…" : "Attach"}
                    </button>
                  </li>
                ))}
              </ul>
              <p className="mt-1 text-xs text-ink-soft">Attaching refreshes the chart-filled answers. Then resubmit above.</p>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-3 text-sm">
          <p className="font-medium">The plan's medical director did not certify this request.</p>
          <p>{pas.reason_text}</p>
          <button className="btn-quiet" disabled={!!busy} onClick={() => act("appeal", () => send<Order>(provider(`/api/orders/${id}/appeal-draft`)))}>
            {busy === "appeal" ? "Drafting…" : order.appeal_draft ? "Redraft appeal" : "Draft an appeal"}
          </button>
          {order.appeal_draft && <textarea className="field doc-text h-80" defaultValue={order.appeal_draft} aria-label="Appeal draft" />}
        </div>
      )}
    </Section>
  );
}
