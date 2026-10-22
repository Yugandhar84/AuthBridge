import Link from "next/link";

export default function Home() {
  return (
    <div className="mx-auto max-w-3xl py-10">
      <h1 className="font-serif text-4xl font-semibold leading-tight tracking-tight">
        Prior authorization, answered while the order is still open.
      </h1>
      <p className="mt-4 max-w-2xl text-lg text-ink-soft">
        AuthBridge connects a clinic and a health plan with the HL7 Da Vinci standards. Coverage rules, evidence and
        decisions live in Snowflake; AI fills in documentation with quotes from the chart, and a clinician makes every
        denial.
      </p>
      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        <Link href="/provider" className="panel block p-5 hover:border-accent">
          <span className="font-serif text-xl font-semibold">Clinic</span>
          <p className="mt-1 text-sm text-ink-soft">
            Order a service, see coverage requirements at signing, complete pre-filled documentation and track the decision.
          </p>
        </Link>
        <Link href="/payer" className="panel block p-5 hover:border-accent">
          <span className="font-serif text-xl font-semibold">Health plan</span>
          <p className="mt-1 text-sm text-ink-soft">
            Review requests criterion by criterion, decide pended cases and ask questions about prior authorization metrics.
          </p>
        </Link>
      </div>
      <ol className="mt-10 space-y-2 text-sm text-ink-soft">
        <li><span className="font-semibold text-ink">1. Coverage check (CRD).</span> Signing an order asks the plan whether prior authorization is needed.</li>
        <li><span className="font-semibold text-ink">2. Documentation (DTR).</span> The plan&apos;s questionnaire opens with answers drawn from the chart.</li>
        <li><span className="font-semibold text-ink">3. Submission (PAS).</span> The request is sent as a FHIR bundle and decided in seconds when the evidence is clear.</li>
      </ol>
    </div>
  );
}
