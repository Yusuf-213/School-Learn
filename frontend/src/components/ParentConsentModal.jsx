import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { ShieldCheck, X } from "@phosphor-icons/react";

const ELIGIBLE_ROLES = new Set(["student", "individual"]);

export default function ParentConsentModal() {
  const { user } = useAuth();
  const [requests, setRequests] = useState([]);
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    if (!user || !ELIGIBLE_ROLES.has(user.role)) { setRequests([]); return; }
    try {
      const { data } = await api.get("/student/parent-consent-requests");
      setRequests(data.requests || []);
    } catch {
      setRequests([]);
    }
  }, [user]);

  useEffect(() => { load(); }, [load]);

  const decide = async (link_id, approved) => {
    setBusy(link_id);
    try {
      await api.post(`/student/parent-consent-requests/${link_id}/decide`, { approved });
      toast.success(approved ? "Access granted — your parent can now see your record." : "Access declined.");
      setRequests((rs) => rs.filter((r) => r.link_id !== link_id));
    } catch (ex) {
      toast.error(ex?.response?.data?.detail || "Could not save your decision");
    } finally {
      setBusy(null);
    }
  };

  if (!user || !ELIGIBLE_ROLES.has(user.role) || requests.length === 0) return null;
  const r = requests[0];

  return (
    <div className="fixed inset-0 z-[100] bg-ink/70 backdrop-blur-sm flex items-center justify-center p-4" data-testid="parent-consent-modal">
      <div className="brutal-card p-6 bg-white max-w-md w-full">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="border-2 border-ink bg-lavender rounded-md p-2 shadow-brutal">
              <ShieldCheck size={22} weight="fill" />
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">Guardian access request</div>
              <div className="font-display font-black text-xl">Is this your legal guardian?</div>
            </div>
          </div>
        </div>
        <p className="text-sm text-[#333] mt-4">
          This email is asking to view your account — homework, progress, and records:
        </p>
        <div className="mt-3 brutal-card p-3 bg-butter">
          <div className="font-mono text-sm break-all" data-testid="parent-consent-email">{r.parent_email}</div>
          {r.parent_name && <div className="text-xs text-[#4A4A4A] mt-1">Name given: <b>{r.parent_name}</b></div>}
          {r.relationship && <div className="text-xs text-[#4A4A4A] mt-1">Relationship: <b>{r.relationship}</b></div>}
        </div>
        <p className="text-xs text-[#4A4A4A] mt-4">
          Only tap <b>Yes</b> if you know this person and they are your legal parent or guardian. Learnify staff will never send you a link like this — if in doubt, tap <b>No</b>.
        </p>
        <div className="mt-5 grid grid-cols-2 gap-2">
          <button onClick={() => decide(r.link_id, false)} disabled={busy === r.link_id}
            className="brutal-btn bg-white disabled:opacity-60 inline-flex items-center justify-center gap-2"
            data-testid="parent-consent-no">
            <X size={14} weight="bold" /> No, block this
          </button>
          <button onClick={() => decide(r.link_id, true)} disabled={busy === r.link_id}
            className="brutal-btn bg-ink text-white disabled:opacity-60 inline-flex items-center justify-center gap-2"
            data-testid="parent-consent-yes">
            <ShieldCheck size={14} weight="bold" /> Yes, they're my guardian
          </button>
        </div>
        {requests.length > 1 && (
          <p className="text-xs text-[#4A4A4A] mt-3 text-center">{requests.length - 1} more waiting after this one.</p>
        )}
      </div>
    </div>
  );
}
