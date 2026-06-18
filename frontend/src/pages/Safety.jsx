import { useEffect, useState } from "react";
import GlobalNav from "@/components/GlobalNav";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { ShieldCheck, Phone, EnvelopeSimple, CheckCircle, Link as LinkIcon } from "@phosphor-icons/react";

export default function Safety() {
  const [info, setInfo] = useState(null);
  useEffect(() => { api.get("/safety/info").then(({ data }) => setInfo(data)).catch(() => {}); }, []);

  return (
    <div className="min-h-screen bg-paper">
      <GlobalNav />
      <main className="max-w-4xl mx-auto px-6 py-10 space-y-8" data-testid="safety-page">
        <div>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A]">Safeguarding & safety</div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Built safe for UK schools.</h1>
          <p className="text-[#4A4A4A] mt-3 max-w-2xl">Learnify is designed to meet UK school safeguarding and accessibility expectations. Here's exactly how, with the policies and contacts you need.</p>
        </div>

        <section className="brutal-card p-6 bg-mint">
          <ShieldCheck size={28} weight="duotone" />
          <h2 className="font-display font-bold text-2xl mt-2">If you're in danger or distressed right now</h2>
          <ul className="mt-3 space-y-2 text-sm">
            <li className="flex items-center gap-2"><Phone size={16} weight="bold" /> <strong>Childline</strong> — 0800 1111 (free, 24/7) · <a className="underline" href="https://www.childline.org.uk" target="_blank" rel="noreferrer">childline.org.uk</a></li>
            <li className="flex items-center gap-2"><Phone size={16} weight="bold" /> <strong>Samaritans</strong> — 116 123 · <a className="underline" href="https://www.samaritans.org" target="_blank" rel="noreferrer">samaritans.org</a></li>
            <li className="flex items-center gap-2"><Phone size={16} weight="bold" /> <strong>NSPCC</strong> — 0808 800 5000</li>
            <li>If you are in immediate danger, dial <strong>999</strong>.</li>
          </ul>
        </section>

        <section className="brutal-card p-6 bg-white">
          <h2 className="font-display font-bold text-2xl">Technical security</h2>
          <ul className="mt-4 grid sm:grid-cols-2 gap-y-2 text-sm">
            <Tick>TLS / HTTPS encryption end-to-end</Tick>
            <Tick>10+ char strong password policy (upper, lower, number, symbol)</Tick>
            <Tick>TOTP multi-factor authentication for staff</Tick>
            <Tick>Server-level firewall + Web Application Firewall</Tick>
            <Tick>Automated daily database backups</Tick>
            <Tick>JWT sessions auto-rotate; explicit 401 ends them</Tick>
            <Tick>Per-row school data isolation</Tick>
            <Tick>Annual security review</Tick>
          </ul>
        </section>

        <section className="brutal-card p-6 bg-white">
          <h2 className="font-display font-bold text-2xl">Content filtering & monitoring</h2>
          <p className="mt-2 text-sm text-[#4A4A4A]">Every AI prompt students send (Homework Helper, AI Tutor, Dreams, Suggestions) is screened before it reaches the model. Harmful content (self-harm, abuse, illegal activity) is blocked and logged. Safeguarding cues trigger an automatic message with Childline + Samaritans details and are flagged in the owner's safety log.</p>
          <ul className="mt-3 text-sm space-y-1 list-disc pl-5">
            <li>Hard-block: harm to self/others, CSAM, illegal drug supply, weapons, sexual violence.</li>
            <li>Safeguard-flag: distress signals ("hopeless", "want to die"), abuse references.</li>
            <li>Reviewed at least annually (last review: {info?.last_review_at || "2026-06-18"}).</li>
          </ul>
        </section>

        <section className="brutal-card p-6 bg-white">
          <h2 className="font-display font-bold text-2xl">Accessibility (WCAG 2.2 AA)</h2>
          <p className="mt-2 text-sm text-[#4A4A4A]">Open the accessibility menu (eye icon, top nav) to enable any of:</p>
          <ul className="mt-3 text-sm space-y-1 list-disc pl-5">
            <li>OpenDyslexic font across the entire app</li>
            <li>High-contrast mode</li>
            <li>Larger text (+25%)</li>
            <li>Reduce motion (disables animation for vestibular sensitivity)</li>
          </ul>
        </section>

        <section className="brutal-card p-6 bg-butter">
          <h2 className="font-display font-bold text-2xl">Statutory information & guidance</h2>
          <ul className="mt-3 text-sm space-y-2">
            {(info?.statutory_links || []).map((l) => (
              <li key={l.url} className="flex items-center gap-2"><LinkIcon size={14} /> <a className="underline" href={l.url} target="_blank" rel="noreferrer">{l.name}</a></li>
            ))}
          </ul>
          <p className="mt-4 text-sm">Schools using Learnify host their own statutory policies (safeguarding, child protection, mobile phone, behaviour, SEN, accessibility, privacy) and Ofsted report links in the school admin panel. Public view: <code>/school/&lt;school_id&gt;/policies</code>.</p>
        </section>

        <section className="brutal-card p-6 bg-white">
          <h2 className="font-display font-bold text-2xl">Contact us</h2>
          <p className="mt-2 text-sm flex items-center gap-2"><EnvelopeSimple size={16} weight="bold" /> Safeguarding · <a className="underline" href={`mailto:${info?.support_email || "safeguarding@learnify.app"}`}>{info?.support_email || "safeguarding@learnify.app"}</a></p>
          <Link to="/contact" className="brutal-btn bg-white hover:bg-butter inline-flex items-center gap-2 mt-4 text-sm">Full contact details →</Link>
        </section>
      </main>
    </div>
  );
}

function Tick({ children }) {
  return <li className="flex items-start gap-2"><CheckCircle size={16} weight="fill" className="mt-0.5 shrink-0" /> {children}</li>;
}
