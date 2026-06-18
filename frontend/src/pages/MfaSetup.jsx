import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { ShieldCheck, QrCode, CheckCircle, XCircle, Warning } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function MfaSetup() {
  const { user, refreshUser } = useAuth();
  const [status, setStatus] = useState(null);
  const [secret, setSecret] = useState(null);
  const [uri, setUri] = useState(null);
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);

  const loadStatus = async () => {
    try { const { data } = await api.get("/auth/mfa/status"); setStatus(data); } catch {}
  };
  useEffect(() => { loadStatus(); }, []);

  const begin = async () => {
    setLoading(true);
    try {
      const { data } = await api.post("/auth/mfa/setup");
      setSecret(data.secret); setUri(data.provisioning_uri);
    } catch (ex) {
      toast.error(ex.response?.data?.detail || "Setup failed");
    } finally { setLoading(false); }
  };

  const verify = async () => {
    setLoading(true);
    try {
      await api.post("/auth/mfa/verify_enroll", { code });
      toast.success("MFA enabled.");
      setSecret(null); setUri(null); setCode("");
      await loadStatus();
      await refreshUser();
    } catch (ex) {
      toast.error(ex.response?.data?.detail || "Code didn't match");
    } finally { setLoading(false); }
  };

  const disable = async () => {
    if (!window.confirm("Turn off MFA? This reduces account security.")) return;
    setLoading(true);
    try {
      await api.post("/auth/mfa/disable", { code });
      toast.success("MFA disabled.");
      setCode("");
      await loadStatus();
    } catch (ex) {
      toast.error(ex.response?.data?.detail || "Disable failed");
    } finally { setLoading(false); }
  };

  const qrUrl = uri ? `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(uri)}` : null;

  return (
    <AppLayout>
      <div className="max-w-2xl space-y-6" data-testid="mfa-page">
        <div className="flex items-center gap-3">
          <ShieldCheck size={28} weight="duotone" />
          <div>
            <div className="text-xs tracking-[0.2em] uppercase font-bold text-[#4A4A4A]">Two-factor authentication</div>
            <h1 className="font-display font-black text-3xl sm:text-4xl tracking-tight">Lock down your account.</h1>
          </div>
        </div>

        {!status?.required_for_role && (
          <div className="brutal-card p-4 bg-butter text-sm flex items-center gap-2">
            <Warning size={18} weight="bold" /> MFA is optional on individual accounts, mandatory for school staff.
          </div>
        )}

        {status?.enabled ? (
          <div className="brutal-card p-6 bg-mint">
            <div className="flex items-center gap-2"><CheckCircle size={22} weight="fill" /><strong className="text-lg">MFA is enabled.</strong></div>
            <p className="text-sm text-[#4A4A4A] mt-2">Every sign-in now requires a 6-digit code from your authenticator app.</p>
            <div className="mt-4 space-y-2">
              <label className="block">
                <span className="text-xs uppercase tracking-[0.2em] font-bold">Disable — confirm with current code</span>
                <input data-testid="mfa-disable-code" inputMode="numeric" maxLength={6} value={code} onChange={(e) => setCode(e.target.value)} className="mt-2 brutal-input w-40 font-mono tracking-widest text-lg" placeholder="000000" />
              </label>
              <button onClick={disable} disabled={loading || code.length !== 6} data-testid="mfa-disable-btn"
                className="brutal-btn bg-white hover:bg-peach text-sm inline-flex items-center gap-2 disabled:opacity-60">
                <XCircle size={16} /> Disable MFA
              </button>
            </div>
          </div>
        ) : !secret ? (
          <div className="brutal-card p-6 space-y-3">
            <p className="text-sm">You'll need an authenticator app (Google Authenticator, 1Password, Microsoft Authenticator, Authy). Scan a QR code, enter the 6-digit code it shows, done.</p>
            <button onClick={begin} disabled={loading} data-testid="mfa-begin-btn"
              className="brutal-btn bg-ink text-white inline-flex items-center gap-2 disabled:opacity-60">
              <QrCode size={16} weight="bold" /> {loading ? "Starting…" : "Set up MFA"}
            </button>
          </div>
        ) : (
          <div className="brutal-card p-6 space-y-4">
            <p className="text-sm"><strong>Step 1.</strong> Open your authenticator app and scan this QR code (or paste the secret).</p>
            {qrUrl && <img src={qrUrl} alt="MFA QR" className="border-2 border-ink rounded-md" />}
            <div className="brutal-input bg-white p-3 font-mono text-xs break-all" data-testid="mfa-secret">{secret}</div>
            <p className="text-sm"><strong>Step 2.</strong> Enter the 6-digit code from the app.</p>
            <input data-testid="mfa-enroll-code" inputMode="numeric" maxLength={6} value={code} onChange={(e) => setCode(e.target.value)}
              className="brutal-input w-40 font-mono tracking-widest text-lg" placeholder="000000" />
            <button onClick={verify} disabled={loading || code.length !== 6} data-testid="mfa-verify-btn"
              className="brutal-btn bg-ink text-white inline-flex items-center gap-2 disabled:opacity-60">
              <CheckCircle size={16} weight="bold" /> {loading ? "Verifying…" : "Confirm and enable"}
            </button>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
