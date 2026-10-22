// One vocabulary for status across the clinic and health-plan screens.
type Tone = "ok" | "pend" | "review" | "deny" | "gold" | "neutral" | "accent";

export const STATUS: Record<string, { label: string; tone: Tone }> = {
  DRAFT: { label: "Draft", tone: "neutral" },
  SIGNED: { label: "Signed", tone: "neutral" },
  NO_AUTH_NEEDED: { label: "No prior auth needed", tone: "neutral" },
  GOLD_CARD: { label: "Gold card – auth satisfied", tone: "gold" },
  DOC_NEEDED: { label: "Documentation needed", tone: "accent" },
  IN_DTR: { label: "Documentation in progress", tone: "accent" },
  SUBMITTED: { label: "Submitted", tone: "accent" },
  APPROVED: { label: "Approved", tone: "ok" },
  PENDED: { label: "Pended", tone: "pend" },
  CLINICIAN_REVIEW: { label: "Clinician review", tone: "review" },
  DENIED: { label: "Denied", tone: "deny" },
  NOT_COVERED: { label: "Not covered", tone: "deny" },
  AUTO_APPROVE: { label: "Auto-approve", tone: "ok" },
  PEND: { label: "Pend", tone: "pend" },
  RECOMMEND_DENY: { label: "Recommend deny – needs clinician", tone: "review" },
  MET: { label: "Met", tone: "ok" },
  NOT_MET: { label: "Not met", tone: "deny" },
  UNKNOWN: { label: "Unknown", tone: "pend" },
  A1: { label: "A1 Certified", tone: "ok" },
  A3: { label: "A3 Not certified", tone: "deny" },
  A4: { label: "A4 Pending", tone: "pend" },
  A6: { label: "A6 Modified", tone: "ok" },
};

export const TONE_CLASS: Record<Tone, string> = {
  ok: "text-ok border-ok",
  pend: "text-pend border-pend",
  review: "text-review border-review",
  deny: "text-deny border-deny",
  gold: "text-gold border-gold",
  neutral: "text-neutral border-neutral",
  accent: "text-accent border-accent",
};

export function toneOf(status?: string | null): Tone {
  return (status && STATUS[status]?.tone) || "neutral";
}

export function ageOf(birthDate: string): number {
  const b = new Date(birthDate);
  const n = new Date();
  let a = n.getFullYear() - b.getFullYear();
  if (n < new Date(n.getFullYear(), b.getMonth(), b.getDate())) a -= 1;
  return a;
}

export function pct(v: number | null | undefined): string {
  return v === null || v === undefined ? "–" : `${(v * 100).toFixed(1)}%`;
}

export function hoursLeft(due: string): number {
  return (new Date(due.endsWith("Z") || due.includes("+") ? due : due + "Z").getTime() - Date.now()) / 3_600_000;
}

export function formatHours(h: number | null | undefined): string {
  if (h === null || h === undefined) return "–";
  if (Math.abs(h) < 1) return `${Math.round(h * 60)} min`;
  if (Math.abs(h) < 48) return `${h.toFixed(1)} h`;
  return `${(h / 24).toFixed(1)} days`;
}

export function display(v: unknown): string {
  if (v === null || v === undefined || v === "") return "not documented";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  return String(v);
}
