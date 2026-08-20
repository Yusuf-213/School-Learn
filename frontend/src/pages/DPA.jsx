import { useEffect, useState } from "react";
import GlobalNav from "@/components/GlobalNav";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Lock, ShieldCheck, FileText, DownloadSimple } from "@phosphor-icons/react";

export default function DPA() {
  const { user } = useAuth();
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState(null);
  const [schoolName, setSchoolName] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [status, setStatus] = useState(null);

  useEffect(() => {
    api.get("/legal/dpa")
      .then(({ data }) => setPayload(data))
      .catch((e) => setError(e?.response?.data?.detail || "Unable to load document"));
    if (user) {
      api.get("/legal/dpa/status").then(({ data }) => setStatus(data)).catch(() => {});
    }
  }, [user]);

  const downloadSignedPdf = async () => {
    setDownloading(true);
    try {
      const res = await api.post("/legal/dpa/signed-pdf", { school_name: schoolName || undefined }, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      const cd = res.headers["content-disposition"] || "";
      const match = cd.match(/filename="?([^"]+)"?/);
      a.href = url;
      a.download = match?.[1] || "Learnify-DPA.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert(e?.response?.data?.detail || "Could not generate PDF");
    } finally {
      setDownloading(false);
    }
  };

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
          {user && status?.accepted && (
            <p className="text-xs text-green-800 mt-2" data-testid="dpa-user-accepted">
              You accepted this version on {new Date(status.accepted_at).toLocaleString()}.
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
                <div className="flex-1">
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

            {user && (
              <section className="brutal-card p-6 bg-butter" data-testid="dpa-download-card">
                <div className="flex items-center gap-2 mb-2">
                  <DownloadSimple size={20} weight="bold" />
                  <h2 className="font-display font-bold text-xl">Signed PDF for your records</h2>
                </div>
                <p className="text-sm text-[#333]">
                  Download a PDF of this DPA cryptographically bound to your school name and today's date.
                </p>
                <div className="mt-3 flex flex-wrap gap-2 items-end">
                  <div className="flex-1 min-w-[220px]">
                    <label className="block text-xs font-bold mb-1">School / Institution name</label>
                    <input
                      type="text"
                      value={schoolName}
                      onChange={(e) => setSchoolName(e.target.value)}
                      placeholder="e.g. St. Mary's Primary School"
                      className="w-full border-2 border-ink rounded-md p-2 text-sm"
                      data-testid="dpa-pdf-school-name"
                    />
                  </div>
                  <button
                    onClick={downloadSignedPdf}
                    disabled={downloading}
                    className="brutal-btn bg-mint hover:bg-white inline-flex items-center gap-2"
                    data-testid="dpa-download-pdf"
                  >
                    <DownloadSimple size={18} weight="bold" />
                    {downloading ? "Preparing…" : "Download signed PDF"}
                  </button>
                </div>
              </section>
            )}

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
