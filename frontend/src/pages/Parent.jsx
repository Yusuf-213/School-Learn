import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Users, Plus, X, ClipboardText } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Parent() {
  const { user } = useAuth();
  const [children, setChildren] = useState([]);
  const [selected, setSelected] = useState(null);
  const [summary, setSummary] = useState(null);
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/parent/children");
      setChildren(data.children || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not load");
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const link = async (e) => {
    e.preventDefault();
    try {
      await api.post("/parent/children", { child_email: email });
      toast.success("Linked");
      setEmail("");
      load();
    } catch (ex) { toast.error(ex?.response?.data?.detail || "Failed"); }
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

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="parent-page">
        <header>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A] flex items-center gap-2">
            <Users size={14} weight="fill" /> Parent portal
          </div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Your children.</h1>
          <p className="text-[#4A4A4A] mt-3">Link your child's account by email — you'll only ever see homework and detentions for the accounts you've linked.</p>
        </header>

        <form onSubmit={link} className="brutal-card p-4 bg-butter flex flex-wrap gap-2 items-center" data-testid="parent-link-form">
          <input className="brutal-input flex-1 min-w-[220px]" type="email" placeholder="child@school.uk" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="parent-link-email" />
          <button className="brutal-btn bg-ink text-white inline-flex items-center gap-2" type="submit" data-testid="parent-link-submit"><Plus size={14} /> Link child</button>
        </form>

        <div className="grid md:grid-cols-3 gap-4">
          <aside className="brutal-card p-4 bg-white">
            <h2 className="font-display font-bold text-lg mb-3">Linked children</h2>
            {loading ? <div className="text-sm text-[#4A4A4A]">Loading…</div> :
              children.length === 0 ? <div className="text-sm text-[#4A4A4A]">No children linked yet.</div> :
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
                  <h3 className="font-display font-bold text-lg mb-2">Detentions</h3>
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
