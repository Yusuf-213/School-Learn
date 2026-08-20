import { useEffect, useState } from "react";
import GlobalNav from "@/components/GlobalNav";
import { api } from "@/lib/api";
import { Lock, ShieldCheck, FileText } from "@phosphor-icons/react";

export default function DPA() {
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get("/legal/dpa")
      .then(({ data }) => setPayload(data))
      .catch((e) => setError(e?.response?.data?.detail || "Unable to load document"));
  }, []);

  const doc = payload?.document;

  return (
    <div className="min-h-screen bg-paper text-ink">
      <GlobalNav />
      <main className="max-w-4xl mx-auto px-6 py-10 space-y-8" data-testid="dpa-page">
        <header>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A] flex items-center gap-2">
            <Lock size={14} weight="fill" /> Encrypted legal document
          </div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight" data-testid="dpa-title">
            {doc?.title || "UK GDPR Privacy Notice & DPA"}
          </h1>
          {payload && (
            <p className="text-sm text-[#4A4A4A] mt-3">
              Version {payload.version} · Effective {payload.effective_date} · Encrypted at rest with {payload.algorithm}.
            </p>
          )}
        </header>

        {error && (
          <div className="brutal-card p-6 bg-peach" data-testid="dpa-error">
            <p className="font-bold">Couldn't load the document.</p>
            <p className="text-sm mt-1">{error}</p>
          </div>
        )}

        {doc && (
          <>
            <section className="brutal-card p-6 bg-mint" data-testid="dpa-integrity">
              <div className="flex items-start gap-3">
                <ShieldCheck size={24} weight="duotone" />
                <div>
                  <h2 className="font-display font-bold text-xl">Integrity & storage</h2>
                  <p className="text-sm mt-1">
                    This document is stored in the Learnify database as ciphertext only and decrypted on request via a server-held key.
                  </p>
                  <p className="text-xs text-[#4A4A4A] mt-2 break-all">
                    SHA-256 checksum · <code>{payload.checksum}</code>
                  </p>
                </div>
              </div>
            </section>

            <section className="brutal-card p-6 bg-white">
              <div className="flex items-center gap-2 mb-3">
                <FileText size={20} weight="bold" />
                <h2 className="font-display font-bold text-xl">Contents</h2>
              </div>
              <ol className="text-sm space-y-1 list-decimal pl-5" data-testid="dpa-contents">
                {doc.contents.map((item) => (
                  <li key={item}>{item.replace(/^\d+\.\s*/, "")}</li>
                ))}
              </ol>
            </section>

            <div className="space-y-6" data-testid="dpa-sections">
              {doc.sections.map((s, idx) => (
                <section key={s.heading} className="brutal-card p-6 bg-white">
                  <h3 className="font-display font-bold text-lg">
                    {idx + 1}. {s.heading}
                  </h3>
                  <p className="text-sm text-[#333] mt-2 leading-relaxed whitespace-pre-line">
                    {s.body}
                  </p>
                </section>
              ))}
            </div>
          </>
        )}

        {!doc && !error && (
          <div className="text-sm text-[#4A4A4A]" data-testid="dpa-loading">Decrypting document…</div>
        )}
      </main>
    </div>
  );
}
