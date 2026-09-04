import { useEffect, useState, useCallback } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Users, Check, X, ShieldCheck } from "@phosphor-icons/react";

const STAFF_ROLES = new Set(["school_admin", "owner"]);

export default function ParentRequests() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);
  const [note, setNote] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/school/parent-requests");
      setRows(data.requests || []);
    } catch (ex) {
      toast.error(ex?.response?.data?.detail || "Could not load requests");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { if (STAFF_ROLES.has(user?.role)) load(); }, [load, user]);

  if (!user || !STAFF_ROLES.has(user.role)) {
    return (
      <AppLayout>
        <div className="brutal-card p-8 max-w-md mx-auto">
          <ShieldCheck size={36} weight="duotone" />
          <h1 className="font-display font-black text-2xl mt-3">School admin only</h1>
          <p className="text-[#4A4A4A] mt-2">Only school admins and the owner can review guardian access requests.</p>
        </div>
      </AppLayout>
    );
  }

  const decide = async (link_id, approved) => {
    setBusy(link_id);
    try {
      await api.post(`/school/parent-requests/${link_id}/decide`, {
        approved,
        note: approved ? null : (note[link_id] || "").trim() || null,
      });
      toast.success(approved ? "Approved — the parent now has read-only access." : "Rejected.");
      setRows((rs) => rs.filter((r) => r.link_id !== link_id));
    } catch (ex) {
      toast.error(ex?.response?.data?.detail || "Decision failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="parent-requests-page">
        <header>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A] flex items-center gap-2">
            <Users size={14} weight="fill" /> Safeguarding · Guardian access
          </div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Parent access requests.</h1>
          <p className="text-[#4A4A4A] mt-3 max-w-2xl">
            A parent has asked to view their child's academic record. Only approve if you can verify the parent is the child's legal guardian. Approvals grant read-only access to homework and detentions.
          </p>
        </header>

        {loading ? (
          <div className="brutal-card p-6 text-[#4A4A4A]">Loading…</div>
        ) : rows.length === 0 ? (
          <div className="brutal-card p-8 text-center bg-white" data-testid="parent-requests-empty">
            <ShieldCheck size={32} weight="duotone" />
            <div className="font-display font-bold text-lg mt-2">No pending requests.</div>
            <p className="text-sm text-[#4A4A4A]">You'll see new guardian access requests here when parents ask to link a child in your school.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {rows.map((r) => (
              <div key={r.link_id} className="brutal-card p-5 bg-white" data-testid={`parent-request-${r.link_id}`}>
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">Parent</div>
                    <div className="font-bold text-lg">{r.parent_name || "—"}</div>
                    <div className="font-mono text-xs text-[#4A4A4A] break-all">{r.parent_email}</div>
                    {r.relationship && <div className="text-xs mt-1">Relationship claimed: <b>{r.relationship}</b></div>}
                    <div className="text-xs text-[#4A4A4A] mt-1">Requested {new Date(r.requested_at).toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">Child</div>
                    <div className="font-bold text-lg">{r.child_name || "—"}</div>
                    <div className="font-mono text-xs text-[#4A4A4A] break-all">{r.child_email}</div>
                    <div className="text-xs mt-1">In your school</div>
                  </div>
                </div>
                <div className="mt-4 grid sm:grid-cols-3 gap-2">
                  <input
                    className="brutal-input sm:col-span-1"
                    placeholder="Optional reason if rejecting"
                    value={note[r.link_id] || ""}
                    onChange={(e) => setNote({ ...note, [r.link_id]: e.target.value })}
                    data-testid={`parent-request-note-${r.link_id}`}
                  />
                  <button onClick={() => decide(r.link_id, false)} disabled={busy === r.link_id}
                    className="brutal-btn bg-white disabled:opacity-60 inline-flex items-center justify-center gap-2"
                    data-testid={`parent-request-reject-${r.link_id}`}>
                    <X size={14} weight="bold" /> Reject
                  </button>
                  <button onClick={() => decide(r.link_id, true)} disabled={busy === r.link_id}
                    className="brutal-btn bg-ink text-white disabled:opacity-60 inline-flex items-center justify-center gap-2"
                    data-testid={`parent-request-approve-${r.link_id}`}>
                    <Check size={14} weight="bold" /> Approve
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
