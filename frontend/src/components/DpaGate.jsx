import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Lock, ShieldCheck, DownloadSimple } from "@phosphor-icons/react";
import { Link } from "react-router-dom";

/**
 * Blocks the entire authenticated area until the user has accepted the current DPA version.
 * Login / register / public pages are NOT wrapped — sign-in still works normally.
 */
export default function DpaGate({ children }) {
  const { user, logout } = useAuth();
  const [status, setStatus] = useState(null); // null=loading, {accepted, ...}
  const [doc, setDoc] = useState(null);
  const [schoolName, setSchoolName] = useState("");
  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState(null);
  const [statusError, setStatusError] = useState(false);

  const loadStatus = () => {
    setStatusError(false);
    api.get("/legal/dpa/status")
      .then(({ data }) => setStatus(data))
      .catch(() => setStatusError(true)); // fail-closed: block until we can confirm acceptance
  };

  useEffect(() => {
    if (!user) return;
    loadStatus();
    api.get("/legal/dpa")
      .then(({ data }) => setDoc(data))
      .catch(() => {});
     
  }, [user]);

  if (!user) return children;
  if (status === null && !statusError) return children; // don't block first paint
  if (!statusError && status?.accepted) return children;

  const onAccept = async () => {
    setAccepting(true);
    setError(null);
    try {
      const { data } = await api.post("/legal/dpa/accept", {
        school_name: schoolName || undefined,
      });
      setStatus({ accepted: true, ...data });
    } catch (e) {
      setError(e?.response?.data?.detail || "Could not record acceptance");
    } finally {
      setAccepting(false);
    }
  };

  const onSignOut = async () => {
    await logout();
    window.location.href = "/login";
  };

  return (
    <div className="fixed inset-0 z-[9999] bg-ink/70 backdrop-blur-sm flex items-center justify-center p-4" data-testid="dpa-gate">
      <div className="bg-paper border-2 border-ink brutal-shadow w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-lg">
        <div className="p-6 border-b-2 border-ink bg-mint">
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-1 flex items-center gap-2">
            <Lock size={14} weight="fill" /> Encrypted legal document
          </div>
          <h2 className="font-display font-black text-2xl">
            {doc?.document?.title || "UK GDPR Privacy Notice & Data Processing Agreement"}
          </h2>
          {doc && (
            <p className="text-xs text-[#333] mt-2">
              Version {doc.version} · Effective {doc.effective_date} · Encrypted with {doc.algorithm}
            </p>
          )}
        </div>

        <div className="p-6 space-y-4">
          <p className="text-sm">
            Before you can use Learnify, please review and accept our Privacy Policy & Data Processing Agreement.
            Your acceptance is <strong>logged, timestamped and encrypted</strong> for Ofsted-grade auditability.
          </p>

          <div className="border-2 border-ink rounded-md p-4 bg-white max-h-56 overflow-y-auto text-xs space-y-3" data-testid="dpa-gate-summary">
            {(doc?.document?.sections || []).slice(0, 6).map((s) => (
              <div key={s.heading}>
                <div className="font-bold">{s.heading}</div>
                <div className="text-[#333]">{s.body}</div>
              </div>
            ))}
            <div>
              <Link to="/dpa" target="_blank" className="underline text-sm">Read the full document →</Link>
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold mb-1">School / Institution (optional)</label>
            <input
              type="text"
              value={schoolName}
              onChange={(e) => setSchoolName(e.target.value)}
              placeholder="e.g. St. Mary's Primary School"
              className="w-full border-2 border-ink rounded-md p-2 text-sm"
              data-testid="dpa-gate-school-name"
            />
            <p className="text-xs text-[#4A4A4A] mt-1">Used on your signed PDF record. Leave blank if not applicable.</p>
          </div>

          {error && (
            <div className="text-sm text-red-700 border-2 border-red-700 rounded p-2 bg-peach" data-testid="dpa-gate-error">{error}</div>
          )}

          {statusError && (
            <div className="text-sm text-red-800 border-2 border-red-800 rounded p-2 bg-peach" data-testid="dpa-gate-status-error">
              We couldn't confirm your acceptance status. Please retry — for compliance we won't unlock the app until this succeeds.
              <button onClick={loadStatus} className="ml-2 underline font-bold" data-testid="dpa-gate-retry">Retry</button>
            </div>
          )}

          <div className="flex flex-wrap gap-3 items-center pt-2">
            <button
              onClick={onAccept}
              disabled={accepting}
              className="brutal-btn bg-mint hover:bg-white inline-flex items-center gap-2"
              data-testid="dpa-gate-accept"
            >
              <ShieldCheck size={18} weight="bold" />
              {accepting ? "Recording…" : "I Accept"}
            </button>
            <Link
              to="/dpa"
              target="_blank"
              className="brutal-btn bg-white hover:bg-butter inline-flex items-center gap-2"
              data-testid="dpa-gate-read-full"
            >
              <DownloadSimple size={18} weight="bold" /> Read full policy
            </Link>
            <button
              onClick={onSignOut}
              className="text-sm underline text-[#4A4A4A] ml-auto"
              data-testid="dpa-gate-decline"
            >
              Decline & sign out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
