"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ErrorNote, StatusPill } from "@/components/ui";
import { get, provider } from "@/lib/api";
import { useClinic } from "@/lib/context";
import { ageOf } from "@/lib/status";
import type { Patient } from "@/lib/types";

export default function PatientList() {
  const { ctx, practitionerId, setPractitionerId } = useClinic();
  const [patients, setPatients] = useState<Patient[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    get<Patient[]>(provider("/api/patients")).then(setPatients).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-serif text-3xl font-semibold tracking-tight">Today&apos;s patients</h1>
          <p className="text-sm text-ink-soft">{ctx?.organization.name ?? "Lakeside Family Medicine"}</p>
        </div>
        <label className="text-sm">
          <span className="field-label">Ordering as</span>
          <select className="field min-w-64" value={practitionerId} onChange={(e) => setPractitionerId(e.target.value)}>
            {ctx?.practitioners.map((p) => (
              <option key={p.practitioner_role_id} value={p.practitioner_role_id}>
                {p.name} – {p.specialty}
              </option>
            ))}
          </select>
        </label>
      </div>
      <ErrorNote error={error && `Could not load patients: ${error}. Is the provider service running on port 8001?`} />
      <ul className="divide-y divide-rule border-y border-rule">
        {(patients ?? []).map((p) => (
          <li key={p.patient_id}>
            <Link
              href={`/provider/patients/${p.patient_id}`}
              className="grid gap-x-6 gap-y-1 px-2 py-4 hover:bg-wash sm:grid-cols-[minmax(0,1.3fr)_minmax(0,1.6fr)_minmax(0,1fr)]"
            >
              <div>
                <div className="font-serif text-lg font-semibold">
                  {p.family}, {p.given}
                </div>
                <div className="text-sm text-ink-soft">
                  {ageOf(p.birth_date)} y · {p.gender} · MRN {p.mrn}
                </div>
              </div>
              <div className="text-sm">
                <div>{p.problems.join("; ")}</div>
                <div className="text-ink-soft">{p.scenario}</div>
              </div>
              <div className="flex flex-col items-start gap-1 text-sm sm:items-end">
                <span className="text-ink-soft">
                  {p.coverage.plan_id} · {p.coverage.member_id}
                </span>
                {p.latest_order && <StatusPill status={p.latest_order.status} />}
              </div>
            </Link>
          </li>
        ))}
        {patients && patients.length === 0 && <li className="py-6 text-sm text-ink-soft">No patients loaded. Check the seed data.</li>}
        {!patients && !error && <li className="py-6 text-sm text-ink-soft">Loading patients…</li>}
      </ul>
    </div>
  );
}
