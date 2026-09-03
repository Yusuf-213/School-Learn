import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { CalendarBlank, Plus, Trash, PaperPlaneTilt, CheckCircle, XCircle, Clock } from "@phosphor-icons/react";
import { toast } from "sonner";

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

// Roles allowed to directly edit the timetable — everyone else uses "propose".
const DIRECT_EDIT_ROLES = new Set(["teacher", "school_admin", "owner"]);

export default function Timetable() {
  const { user } = useAuth();
  const canDirectEdit = user && (user.role === "owner" || DIRECT_EDIT_ROLES.has(user.role));
  const canApprove = user && (user.role === "school_admin" || user.role === "owner");

  const [recurring, setRecurring] = useState([]);
  const [overrides, setOverrides] = useState([]);
  const [proposals, setProposals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ day_of_week: 0, start_time: "09:00", end_time: "10:00", subject: "", room: "" });
  const [note, setNote] = useState("");
  const [busyId, setBusyId] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [{ data: tt }, { data: props }] = await Promise.all([
        api.get("/timetable"),
        api.get("/timetable/proposals", { params: { status: "pending" } }),
      ]);
      setRecurring(tt.recurring || []);
      setOverrides(tt.overrides || []);
      setProposals(props.items || []);
    } catch {
      toast.error("Could not load timetable");
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.subject.trim()) return;
    const entry = { ...form, day_of_week: Number(form.day_of_week) };
    try {
      if (canDirectEdit) {
        await api.post("/timetable/entries", entry);
        toast.success("Entry added");
      } else {
        await api.post("/timetable/proposals", { action: "add", entry, note: note.trim() || undefined });
        toast.success("Suggestion sent to SLT for approval");
        setNote("");
      }
      setForm({ day_of_week: 0, start_time: "09:00", end_time: "10:00", subject: "", room: "" });
      load();
    } catch (ex) { toast.error(ex?.response?.data?.detail || "Failed"); }
  };

  const removeOrPropose = async (id) => {
    try {
      if (canDirectEdit) {
        await api.delete(`/timetable/entries/${id}`);
        toast.success("Removed");
      } else {
        const reason = window.prompt("Why should this lesson be removed? (optional)") || "";
        await api.post("/timetable/proposals", { action: "remove", target_entry_id: id, note: reason || undefined });
        toast.success("Removal request sent to SLT");
      }
      load();
    } catch (ex) { toast.error(ex?.response?.data?.detail || "Failed"); }
  };

  const decide = async (p, approve) => {
    setBusyId(p.proposal_id);
    try {
      let reason = null;
      if (!approve) {
        reason = window.prompt("Reason for rejection (optional)") || null;
      }
      await api.post(`/timetable/proposals/${p.proposal_id}/${approve ? "approve" : "reject"}`, { reason });
      toast.success(approve ? "Approved and applied" : "Rejected");
      load();
    } catch (ex) { toast.error(ex?.response?.data?.detail || "Failed"); }
    finally { setBusyId(null); }
  };

  const byDay = Array.from({ length: 7 }, () => []);
  recurring.forEach((r) => { if (byDay[r.day_of_week]) byDay[r.day_of_week].push(r); });
  byDay.forEach((arr) => arr.sort((a, b) => a.start_time.localeCompare(b.start_time)));

  const myPending = proposals.filter((p) => p.proposed_by === user?.user_id);

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="timetable-page">
        <header>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A] flex items-center gap-2">
            <CalendarBlank size={14} weight="fill" /> Weekly timetable
          </div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Timetable.</h1>
          <p className="text-[#4A4A4A] mt-3">
            {canDirectEdit
              ? "Recurring weekly schedule. Add or remove lessons directly."
              : "Suggest a change and your school's SLT will review it. You'll only see suggestions from your own school."}
          </p>
        </header>

        {canApprove && proposals.length > 0 && (
          <section className="brutal-card p-6 bg-lavender" data-testid="tt-proposal-inbox">
            <h2 className="font-display font-bold text-xl mb-3 flex items-center gap-2">
              <Clock size={18} weight="duotone" /> Pending suggestions ({proposals.length})
            </h2>
            <ul className="space-y-2">
              {proposals.map((p) => (
                <li key={p.proposal_id} className="brutal-card p-3 bg-white flex flex-wrap items-center justify-between gap-3" data-testid={`tt-proposal-${p.proposal_id}`}>
                  <div className="text-sm min-w-0">
                    <div className="font-bold uppercase text-[10px] tracking-wider text-[#4A4A4A]">{p.action}</div>
                    {p.action === "add" && p.entry && (
                      <div>{DAY_LABELS[p.entry.day_of_week]} · {p.entry.start_time}–{p.entry.end_time} · <strong>{p.entry.subject}</strong>{p.entry.room ? ` · ${p.entry.room}` : ""}</div>
                    )}
                    {p.action === "remove" && (
                      <div>Remove entry <code className="font-mono text-xs">{p.target_entry_id}</code></div>
                    )}
                    <div className="text-xs text-[#4A4A4A] mt-1">
                      By {p.proposed_by_email || p.proposed_by} · {new Date(p.created_at).toLocaleString()}
                    </div>
                    {p.note && <div className="text-xs italic mt-1 text-ink">"{p.note}"</div>}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => decide(p, true)}
                      disabled={busyId === p.proposal_id}
                      className="brutal-btn bg-ink text-white text-xs inline-flex items-center gap-1 disabled:opacity-60"
                      data-testid={`tt-approve-${p.proposal_id}`}
                    >
                      <CheckCircle size={14} weight="bold" /> Approve
                    </button>
                    <button
                      onClick={() => decide(p, false)}
                      disabled={busyId === p.proposal_id}
                      className="brutal-btn bg-white hover:bg-peach text-xs inline-flex items-center gap-1 disabled:opacity-60"
                      data-testid={`tt-reject-${p.proposal_id}`}
                    >
                      <XCircle size={14} weight="bold" /> Reject
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

        {!canApprove && myPending.length > 0 && (
          <section className="brutal-card p-4 bg-butter text-sm" data-testid="tt-my-pending">
            <div className="flex items-center gap-2 font-bold mb-1"><Clock size={14} weight="bold" /> Awaiting SLT approval</div>
            <ul className="list-disc pl-5">
              {myPending.map((p) => (
                <li key={p.proposal_id}>
                  {p.action === "add" && p.entry
                    ? <>Add: {DAY_LABELS[p.entry.day_of_week]} {p.entry.start_time}–{p.entry.end_time} <strong>{p.entry.subject}</strong></>
                    : <>Remove: {p.target_entry_id}</>}
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="brutal-card p-6 bg-butter" data-testid="timetable-add-form">
          <h2 className="font-display font-bold text-xl mb-3">{canDirectEdit ? "Add recurring lesson" : "Suggest a new lesson"}</h2>
          <form onSubmit={submit} className="grid sm:grid-cols-2 md:grid-cols-5 gap-3">
            <select className="brutal-input" value={form.day_of_week} onChange={(e) => setForm({ ...form, day_of_week: e.target.value })} data-testid="tt-day">
              {DAY_LABELS.map((d, i) => <option key={d} value={i}>{d}</option>)}
            </select>
            <input className="brutal-input" type="time" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} data-testid="tt-start" />
            <input className="brutal-input" type="time" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} data-testid="tt-end" />
            <input className="brutal-input" placeholder="Subject" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} data-testid="tt-subject" />
            <input className="brutal-input" placeholder="Room" value={form.room} onChange={(e) => setForm({ ...form, room: e.target.value })} data-testid="tt-room" />
            {!canDirectEdit && (
              <input
                className="brutal-input sm:col-span-2 md:col-span-5"
                placeholder="Optional note for SLT — why do you want this change?"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                data-testid="tt-note"
              />
            )}
            <button className="brutal-btn bg-ink text-white sm:col-span-2 md:col-span-5 inline-flex justify-center items-center gap-2" type="submit" data-testid="tt-add">
              {canDirectEdit ? <><Plus size={16} weight="bold" /> Add lesson</> : <><PaperPlaneTilt size={16} weight="bold" /> Send suggestion to SLT</>}
            </button>
          </form>
        </section>

        {loading ? (
          <div className="brutal-card p-6 text-[#4A4A4A]">Loading…</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-5 gap-2" data-testid="timetable-grid">
            {DAY_LABELS.slice(0, 5).map((d, i) => (
              <div key={d} className="brutal-card p-3 bg-white">
                <div className="font-display font-bold text-sm mb-2">{d}</div>
                {byDay[i].length === 0 && <div className="text-xs text-[#4A4A4A]">—</div>}
                {byDay[i].map((r) => (
                  <div key={r.entry_id} className="border-2 border-ink rounded-md p-2 mb-1 bg-mint text-xs" data-testid={`tt-entry-${r.entry_id}`}>
                    <div className="font-mono">{r.start_time}–{r.end_time}</div>
                    <div className="font-bold">{r.subject}</div>
                    {r.room && <div className="text-[10px] text-[#4A4A4A]">{r.room}</div>}
                    <button onClick={() => removeOrPropose(r.entry_id)} className="mt-1 text-[10px] underline inline-flex items-center gap-1">
                      <Trash size={10} /> {canDirectEdit ? "Remove" : "Suggest remove"}
                    </button>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}

        {overrides.length > 0 && (
          <section className="brutal-card p-6 bg-peach">
            <h3 className="font-display font-bold text-lg mb-2">One-off overrides</h3>
            <ul className="text-sm space-y-1">
              {overrides.map((o) => (
                <li key={o.override_id}>{o.date} — {o.replacement?.subject || "(cancelled)"}</li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </AppLayout>
  );
}
