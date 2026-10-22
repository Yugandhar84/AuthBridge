"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ErrorNote, Section, StatusPill } from "@/components/ui";
import { get, provider, send } from "@/lib/api";
import { useClinic } from "@/lib/context";
import { ageOf } from "@/lib/status";
import type { Order, PatientDetail } from "@/lib/types";

const FREQUENCIES = [
  ["once", "Once"],
  ["daily", "Daily"],
  ["twice-daily", "Twice daily"],
  ["nightly", "Nightly"],
  ["weekly", "Weekly"],
  ["continuous", "Continuous"],
];
const ROUTES = [
  ["subcutaneous", "Subcutaneous"],
  ["oral", "Oral"],
  ["intravenous", "Intravenous"],
  ["intramuscular", "Intramuscular"],
  ["inhalation", "Inhalation"],
];

export default function PatientChart() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { ctx, practitioner, practitionerId } = useClinic();
  const [patient, setPatient] = useState<PatientDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    code: "",
    reason_code: "",
    frequency: "once",
    route: "subcutaneous",
    duration_value: "",
    duration_unit: "mo",
    quantity: "1",
    priority: "standard",
    note: "",
  });

  useEffect(() => {
    get<PatientDetail>(provider(`/api/patients/${id}`))
      .then((p) => {
        setPatient(p);
        setForm((f) => ({ ...f, code: f.code || p.suggested_order, reason_code: f.reason_code || p.suggested_reason }));
      })
      .catch((e) => setError(e.message));
  }, [id]);

  const item = useMemo(() => ctx?.catalog.find((c) => c.code === form.code), [ctx, form.code]);
  const isMed = item?.resource_type === "MedicationRequest";
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [k]: e.target.value });

  async function placeOrder(sign: boolean) {
    setBusy(true);
    setError(null);
    try {
      const reason = ctx?.diagnoses.find((d) => d.code === form.reason_code);
      const order = await send<Order>(provider("/api/orders"), {
        ...form,
        route: isMed ? form.route : null,
        reason_display: reason?.display,
        patient_id: id,
        practitioner_role_id: practitionerId,
      });
      if (sign) await send<Order>(provider(`/api/orders/${order.order_id}/sign`));
      router.push(`/provider/orders/${order.order_id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  if (!patient) return <ErrorNote error={error} />;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/provider" className="text-sm text-accent hover:underline">
          All patients
        </Link>
        <h1 className="mt-1 font-serif text-3xl font-semibold tracking-tight">
          {patient.given} {patient.family}
        </h1>
        <p className="text-sm text-ink-soft">
          {ageOf(patient.birth_date)} y · {patient.gender} · born {patient.birth_date} · MRN {patient.mrn} · {patient.coverage.plan_id}, member{" "}
          {patient.coverage.member_id}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
        <div className="space-y-6">
          <Section title="Chart notes">
            <div className="space-y-5">
              {patient.notes.map((n) => (
                <article key={n.doc_id}>
                  <header className="flex flex-wrap items-baseline gap-x-3 text-sm">
                    <span className="font-semibold">{n.title}</span>
                    <span className="text-ink-soft">
                      {n.note_type} · {n.encounter_date}
                    </span>
                  </header>
                  <p className="doc-text mt-1">{n.text}</p>
                </article>
              ))}
            </div>
          </Section>
          {patient.pending_documents.length > 0 && (
            <Section title="Scanned documents not yet in the chart">
              <ul className="space-y-1 text-sm">
                {patient.pending_documents.map((d) => (
                  <li key={d.doc_id}>
                    {d.title} <span className="text-ink-soft">({d.note_type}, {d.encounter_date})</span>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-ink-soft">These can be attached to a prior authorization if the plan asks for them.</p>
            </Section>
          )}
        </div>

        <div className="space-y-6">
          <Section title="New order">
            <form
              className="grid gap-4 sm:grid-cols-2"
              onSubmit={(e) => {
                e.preventDefault();
                placeOrder(true);
              }}
            >
              <label className="sm:col-span-2">
                <span className="field-label">Service or medication</span>
                <select className="field" value={form.code} onChange={set("code")} required>
                  {ctx?.catalog.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.display} ({c.code_system} {c.code})
                    </option>
                  ))}
                </select>
              </label>
              <label className="sm:col-span-2">
                <span className="field-label">Reason (ICD-10)</span>
                <select className="field" value={form.reason_code} onChange={set("reason_code")}>
                  {ctx?.diagnoses.map((d) => (
                    <option key={d.code} value={d.code}>
                      {d.code} – {d.display}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span className="field-label">Frequency</span>
                <select className="field" value={form.frequency} onChange={set("frequency")}>
                  {FREQUENCIES.map(([v, l]) => (
                    <option key={v} value={v}>
                      {l}
                    </option>
                  ))}
                </select>
              </label>
              {isMed ? (
                <label>
                  <span className="field-label">Route</span>
                  <select className="field" value={form.route} onChange={set("route")}>
                    {ROUTES.map(([v, l]) => (
                      <option key={v} value={v}>
                        {l}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <label>
                  <span className="field-label">Quantity</span>
                  <input className="field" type="number" min={1} value={form.quantity} onChange={set("quantity")} />
                </label>
              )}
              <div>
                <span className="field-label">Duration</span>
                <div className="flex gap-2">
                  <input className="field" type="number" min={1} placeholder="e.g. 3" value={form.duration_value} onChange={set("duration_value")} aria-label="Duration" />
                  <select className="field w-28" value={form.duration_unit} onChange={set("duration_unit")} aria-label="Duration unit">
                    <option value="d">days</option>
                    <option value="wk">weeks</option>
                    <option value="mo">months</option>
                  </select>
                </div>
              </div>
              <fieldset>
                <legend className="field-label">Priority</legend>
                <div className="flex gap-4 pt-2 text-sm">
                  <label className="flex items-center gap-2">
                    <input type="radio" name="priority" value="standard" checked={form.priority === "standard"} onChange={set("priority")} /> Standard
                  </label>
                  <label className="flex items-center gap-2">
                    <input type="radio" name="priority" value="expedited" checked={form.priority === "expedited"} onChange={set("priority")} /> Urgent
                  </label>
                </div>
              </fieldset>
              <label className="sm:col-span-2">
                <span className="field-label">Note to performer (optional)</span>
                <textarea className="field" rows={2} value={form.note} onChange={set("note")} />
              </label>
              <div className="flex flex-wrap items-center gap-3 sm:col-span-2">
                <button className="btn-primary" type="submit" disabled={busy}>
                  {busy ? "Checking coverage…" : "Sign order"}
                </button>
                <button className="btn-quiet" type="button" disabled={busy} onClick={() => placeOrder(false)}>
                  Save draft
                </button>
                <span className="text-xs text-ink-soft">Signing as {practitioner?.name ?? "…"}</span>
              </div>
              <div className="sm:col-span-2">
                <ErrorNote error={error} />
              </div>
            </form>
          </Section>

          <Section title="Orders">
            {patient.orders.length === 0 ? (
              <p className="text-sm text-ink-soft">No orders yet. Signing an order checks coverage with the plan.</p>
            ) : (
              <ul className="divide-y divide-rule">
                {patient.orders.map((o) => (
                  <li key={o.order_id}>
                    <Link href={`/provider/orders/${o.order_id}`} className="flex items-center justify-between gap-3 py-2.5 hover:bg-wash">
                      <span className="text-sm">
                        {o.display}
                        <span className="block text-xs text-ink-soft">{new Date(o.updated_at).toLocaleString()}</span>
                      </span>
                      <StatusPill status={o.status} />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Section>
        </div>
      </div>
    </div>
  );
}
