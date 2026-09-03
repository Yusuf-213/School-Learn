import AppLayout from "@/components/AppLayout";
import { Link } from "react-router-dom";
import { FileText, Archive } from "@phosphor-icons/react";

const OLD_POLICY_TITLE = "SCHOOL LEARN — LEGACY PRIVACY POLICY (v1.0)";
const OLD_POLICY_BODY = `
This is the previous privacy policy that was in force prior to the current UK GDPR
Privacy Notice (v2.0). It is retained here for auditability.

1. Introduction — School Learn provides educational technology to UK schools.
2. What we collect — Names, school email addresses, learning progress, homework and lesson content.
3. Purposes — Deliver the platform, safeguard pupils, run assessment and reporting.
4. Lawful basis — Legitimate interests and school contract.
5. Retention — Personal data retained for the duration of the school subscription.
6. Rights — Access, rectification, erasure via the school data controller.
7. Sub-processors — Hosting, database, AI content generation (documented on request).
8. International transfers — SCCs / IDTA where applicable.
9. Complaints — Contact your school DPO or the ICO.

Superseded by the current UK GDPR Privacy Notice on 2026-02-21.
`.trim();

export default function Legal() {
  return (
    <AppLayout>
      <div className="space-y-8" data-testid="legal-page">
        <header>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A] flex items-center gap-2">
            <FileText size={14} weight="fill" /> Legal
          </div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Legal.</h1>
          <p className="text-[#4A4A4A] mt-3">
            Current privacy notice, DPA acceptance and the historical policy that preceded it.
          </p>
        </header>

        <section className="brutal-card p-6 bg-mint" data-testid="legal-current">
          <h2 className="font-display font-bold text-2xl">Current — UK GDPR Privacy Notice & DPA (v2.0)</h2>
          <p className="text-sm mt-2">
            Full document (encrypted at rest, includes 30-day learning-progress reset per Section 11):
          </p>
          <Link to="/dpa" className="brutal-btn bg-white hover:bg-butter inline-block mt-3" data-testid="legal-open-dpa">
            Read the full DPA →
          </Link>
        </section>

        <section className="brutal-card p-6 bg-white" data-testid="legal-old">
          <div className="flex items-center gap-2 mb-3">
            <Archive size={20} weight="bold" />
            <h2 className="font-display font-bold text-2xl">{OLD_POLICY_TITLE}</h2>
          </div>
          <pre className="text-sm whitespace-pre-wrap font-sans leading-relaxed text-[#333]">
            {OLD_POLICY_BODY}
          </pre>
        </section>

        <section className="brutal-card p-6 bg-butter">
          <h2 className="font-display font-bold text-xl">Data-protection contact</h2>
          <p className="text-sm mt-2">
            All rights requests, breach reports, and audit queries:{" "}
            <a href="mailto:schoollearnsupport@pm.me" className="underline font-bold">
              schoollearnsupport@pm.me
            </a>
          </p>
        </section>
      </div>
    </AppLayout>
  );
}
