import { useCallback, useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Users, Plus, X, ClipboardText, Clock, ShieldWarning, CheckCircle } from "@phosphor-icons/react";
import { toast } from "sonner";

const STATUS_LABEL = {
  pending_school: "Awaiting school approval",
  pending_child_consent: "Waiting for your child's consent",
  approved: "Approved",
  rejected: "Declined",
};

const STATUS_BG = {
  pending_school: "bg-butter",
  pending_child_consent: "bg-lavender",
  approved: "bg-mint",
  rejected: "bg-peach",
};

export default function Parent() {
  const { user } = useAuth();
  const [children, setChildren] = useState([]);
  const [requests, setRequests] = useState([]);
  const [selected, setSelected] = useState(null);
  const [summary, setSummary] = useState(null);
  const [form, setForm] = useState({ child_email: "", relationship: "guardian" });
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [c, r] = await Promise.all([
        api.get("/parent/children"),
        api.get("/parent/link-requests"),
      ]);
      setChildren(c.data.children || []);
      setRequests(r.data.requests || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const request = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post("/parent/link-requests", {
        child_email: form.child_email.trim().toLowerCase(),
        relationship: form.relationship,
      });
      if (data.already_requested) {
        toast.info("You've already asked about this child — check their status below.");
      } else if (data.link?.status === "pending_school") {
        toast.success("Request sent to the child's school for approval.");
      } else {
        toast.success("Request sent — your child needs to confirm you're their guardian.");
      }
      setForm({ child_email: "", relationship: "guardian" });
      load();
    } catch (ex) {
      toast.error(ex?.response?.data?.detail || "Failed");
    } finally {
      setBusy(false);
    }
  };

  const unlink = async (childEmail) => {
    try {
      await api.request({ method: "DELETE", url: "/parent/children", data: { child_email: childEmail } });
      load();
      setSelected(null); setSummary(null);
    } catch (ex) { toast.error(ex?.response?.data?.detail || "Failed"); }
  };

  const open = async (c) => {
    setSelected(c);
    try {
      const { data } = await api.get(`/parent/children/${c.child_user_id}/summary`);
      setSummary(data);
    } catch (ex) { toast.error("Could not load child summary"); }
  };

  if (!user || (user.role !== "parent" && user.role !== "owner")) {
    return (
      <AppLayout>
        <div className="brutal-card p-8 max-w-md mx-auto">
          <Users size={36} weight="duotone" />
          <h1 className="font-display font-black text-2xl mt-3">Parents only</h1>
          <p className="text-[#4A4A4A] mt-2">Sign up as a parent to link and review your child's account.</p>
        </div>
      </AppLayout>
    );
  }

  const pending = requests.filter((r) => r.status === "pending_school" || r.status === "pending_child_consent");
  const rejected = requests.filter((r) => r.status === "rejected");

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="parent-page">
        <header>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A] flex items-center gap-2">
            <Users size={14} weight="fill" /> Parent portal
          </div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Your children.</h1>
          <p className="text-[#4A4A4A] mt-3 max-w-2xl">
            Ask to link your child's account by email. If they're in a school, the school's admin will approve it. If they're studying on their own, they'll get a popup asking to confirm you're their guardian. Parents don't pay.
          </p>
        </header>

        <form onSubmit={request} className="brutal-card p-4 bg-butter grid sm:grid-cols-3 gap-2 items-end" data-testid="parent-link-form">
          <label className="block sm:col-span-2">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Child's email</span>
            <input className="brutal-input w-full mt-2" type="email" placeholder="child@school.uk"
              required data-testid="parent-link-email"
              value={form.child_email}
              onChange={(e) => setForm({ ...form, child_email: e.target.value })} />
          </label>
          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Relationship</span>
            <select className="brutal-input w-full mt-2" data-testid="parent-link-relationship"
              value={form.relationship}
              onChange={(e) => setForm({ ...form, relationship: e.target.value })}>
              <option value="mother">Mother</option>
              <option value="father">Father</option>
              <option value="guardian">Legal guardian</option>
              <option value="other">Other</option>
            </select>
          </label>
          <div className="sm:col-span-3">
            <button className="brutal-btn bg-ink text-white inline-flex items-center gap-2" type="submit"
              disabled={busy} data-testid="parent-link-submit">
              <Plus size={14} /> {busy ? "Sending…" : "Request access"}
            </button>
          </div>
        </form>

        {pending.length > 0 && (
          <section className="space-y-2" data-testid="parent-pending-list">
            <h2 className="font-display font-bold text-lg flex items-center gap-2"><Clock size={16} weight="bold" /> Pending requests</h2>
            {pending.map((r) => (
              <div key={r.link_id} className={`brutal-card p-3 ${STATUS_BG[r.status] || "bg-white"} flex flex-wrap items-center gap-3`} data-testid={`parent-pending-${r.link_id}`}>
                <div className="flex-1 min-w-[220px]">
                  <div className="font-bold">{r.child_name || r.child_email}</div>
                  <div className="text-xs font-mono text-[#4A4A4A]">{r.child_email}</div>
                </div>
                <span className="px-2 py-0.5 border-2 border-ink rounded-md bg-white text-xs font-bold uppercase whitespace-nowrap">
                  {STATUS_LABEL[r.status] || r.status}
                </span>
              </div>
            ))}
          </section>
        )}

        {rejected.length > 0 && (
          <section className="space-y-2" data-testid="parent-rejected-list">
            <h2 className="font-display font-bold text-lg flex items-center gap-2"><X size={16} weight="bold" /> Declined requests</h2>
            <p className="text-xs text-[#4A4A4A]">Try asking again once you've spoken with the school or your child.</p>
            {rejected.map((r) => (
              <div key={r.link_id} className={`brutal-card p-3 ${STATUS_BG[r.status]} flex flex-wrap items-center gap-3`} data-testid={`parent-rejected-${r.link_id}`}>
                <div className="flex-1 min-w-[220px]">
                  <div className="font-bold">{r.child_name || r.child_email}</div>
                  <div className="text-xs font-mono text-[#4A4A4A]">{r.child_email}</div>
                  {r.rejection_reason && <div className="text-xs text-red-800 mt-1">Reason: {r.rejection_reason}</div>}
                </div>
                <span className="px-2 py-0.5 border-2 border-ink rounded-md bg-white text-xs font-bold uppercase whitespace-nowrap">
                  {STATUS_LABEL[r.status] || r.status}
                </span>
              </div>
            ))}
          </section>
        )}

        <div className="grid md:grid-cols-3 gap-4">
          <aside className="brutal-card p-4 bg-white">
            <h2 className="font-display font-bold text-lg mb-3 flex items-center gap-2"><CheckCircle size={16} weight="bold" /> Linked children</h2>
            {loading ? <div className="text-sm text-[#4A4A4A]">Loading…</div> :
              children.length === 0 ? <div className="text-sm text-[#4A4A4A]">No approved children yet. Requests appear here once approved.</div> :
              <ul className="space-y-1">
                {children.map((c) => (
                  <li key={c.child_user_id}>
                    <button onClick={() => open(c)} data-testid={`parent-child-${c.child_user_id}`}
                      className={`w-full text-left px-3 py-2 rounded-md border-2 border-ink text-sm font-bold flex justify-between items-center ${selected?.child_user_id === c.child_user_id ? "bg-mint" : "bg-white hover:bg-butter"}`}>
                      <span>{c.child_name || c.child_email}</span>
                      <span className="text-xs font-mono text-[#4A4A4A]">{c.homework || 0}HW · {c.detentions || 0}D</span>
                    </button>
                  </li>
                ))}
              </ul>
            }
          </aside>

          <section className="md:col-span-2 space-y-3">
            {!selected ? (
              <div className="brutal-card p-8 text-center text-[#4A4A4A]">Pick a child to see their homework and detentions.</div>
            ) : (
              <>
                <div className="brutal-card p-5 bg-mint flex justify-between items-start">
                  <div>
                    <h2 className="font-display font-black text-2xl">{selected.child_name || selected.child_email}</h2>
                    <div className="text-xs text-[#4A4A4A] font-mono mt-1">{selected.child_email}</div>
                  </div>
                  <button onClick={() => unlink(selected.child_email)} className="text-xs underline text-red-800 inline-flex items-center gap-1" data-testid="parent-unlink"><X size={12} /> Unlink</button>
                </div>
                <div className="brutal-card p-5 bg-white">
                  <h3 className="font-display font-bold text-lg mb-2 flex items-center gap-2"><ClipboardText size={16} /> Homework</h3>
                  {(!summary?.homework || summary.homework.length === 0) ? <div className="text-sm text-[#4A4A4A]">None on record.</div> : (
                    <ul className="text-sm space-y-1">
                      {summary.homework.map((h) => <li key={h.homework_id}>{h.title} · <span className="text-[#4A4A4A]">{h.subject}</span></li>)}
                    </ul>
                  )}
                </div>
                <div className="brutal-card p-5 bg-peach">
                  <h3 className="font-display font-bold text-lg mb-2 flex items-center gap-2"><ShieldWarning size={16} /> Detentions</h3>
                  {(!summary?.detentions || summary.detentions.length === 0) ? <div className="text-sm text-[#4A4A4A]">None on record.</div> : (
                    <ul className="text-sm space-y-1">
                      {summary.detentions.map((d) => <li key={d.detention_id}>{d.reason} — {d.status || "issued"}</li>)}
                    </ul>
                  )}
                </div>
              </>
            )}
          </section>
        </div>
      </div>
    </AppLayout>
  );
}
