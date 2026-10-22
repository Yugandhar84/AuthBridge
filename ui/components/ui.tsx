"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { get, provider } from "@/lib/api";
import { STATUS, TONE_CLASS, toneOf } from "@/lib/status";

export function StatusPill({ status, label }: { status?: string | null; label?: string }) {
  if (!status) return null;
  const tone = toneOf(status);
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold ${TONE_CLASS[tone]}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
      {label || STATUS[status]?.label || status}
    </span>
  );
}

export function TopBar() {
  const path = usePathname();
  const [mode, setMode] = useState<{ backend: string; ai: string } | null>(null);
  useEffect(() => {
    get<{ backend: string; ai: string }>(provider("/health")).then(setMode).catch(() => setMode(null));
  }, []);
  const side = path.startsWith("/payer") ? "payer" : path.startsWith("/provider") ? "provider" : null;
  return (
    <header className="border-b border-rule bg-paper">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
        <Link href="/" className="font-serif text-xl font-semibold tracking-tight text-ink">
          AuthBridge
        </Link>
        <nav className="flex rounded-md border border-rule p-0.5 text-sm" aria-label="Switch side">
          <Link
            href="/provider"
            className={`rounded px-3 py-1 ${side === "provider" ? "bg-accent text-paper" : "text-ink-soft hover:text-ink"}`}
          >
            Clinic
          </Link>
          <Link
            href="/payer"
            className={`rounded px-3 py-1 ${side === "payer" ? "bg-accent text-paper" : "text-ink-soft hover:text-ink"}`}
          >
            Health plan
          </Link>
        </nav>
        {side === "payer" && (
          <nav className="flex gap-4 text-sm">
            <Link href="/payer" className={path === "/payer" ? "font-semibold text-ink" : "text-ink-soft hover:text-ink"}>Work queue</Link>
            <Link href="/payer/analytics" className={path === "/payer/analytics" ? "font-semibold text-ink" : "text-ink-soft hover:text-ink"}>Analytics</Link>
          </nav>
        )}
        <span className="ml-auto text-xs text-ink-soft">
          {mode ? `Data: ${mode.backend === "snowflake" ? "Snowflake" : "local mock"} · AI: ${mode.ai === "cortex" ? "Cortex" : "mock"}` : "Services offline"}
          {" · synthetic patients only"}
        </span>
      </div>
    </header>
  );
}

export function ErrorNote({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <p role="alert" className="rounded-md border border-deny px-3 py-2 text-sm text-deny">
      {error}
    </p>
  );
}

export function Section({ title, aside, children }: { title: string; aside?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="panel">
      <div className="flex items-center justify-between gap-3 border-b border-rule px-4 py-2.5">
        <h2 className="text-sm font-semibold text-ink">{title}</h2>
        {aside}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

export function JsonBlock({ value }: { value: unknown }) {
  return (
    <pre className="max-h-96 overflow-auto rounded-md bg-wash p-3 text-xs leading-relaxed text-ink">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

/** Highlights `quote` inside `text` (exact match, whitespace-normalised). */
export function Highlighted({ text, quotes }: { text: string; quotes: string[] }) {
  const norm = (s: string) => s.replace(/\s+/g, " ").trim();
  const t = norm(text);
  const ranges: [number, number][] = [];
  for (const q of quotes) {
    const i = t.indexOf(norm(q));
    if (q && i >= 0) ranges.push([i, i + norm(q).length]);
  }
  ranges.sort((a, b) => a[0] - b[0]);
  const parts: React.ReactNode[] = [];
  let cursor = 0;
  ranges.forEach(([s, e], k) => {
    if (s < cursor) return;
    parts.push(t.slice(cursor, s));
    parts.push(<mark key={k} className="mark-quote text-ink">{t.slice(s, e)}</mark>);
    cursor = e;
  });
  parts.push(t.slice(cursor));
  return <>{parts}</>;
}
