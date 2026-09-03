import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { CalendarBlank, Plus, Trash } from "@phosphor-icons/react";
import { toast } from "sonner";

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function Timetable() {
  const [recurring, setRecurring] = useState([]);
  const [overrides, setOverrides] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ day_of_week: 0, start_time: "09:00", end_time: "10:00", subject: "", room: "" });

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/timetable");
      setRecurring(data.recurring || []);
      setOverrides(data.overrides || []);
    } catch {
      toast.error("Could not load timetable");
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const add = async (e) => {
    e.preventDefault();
    if (!form.subject.trim()) return;
    try {
      await api.post("/timetable/entries", { ...form, day_of_week: Number(form.day_of_week) });
      toast.success("Entry added");
      setForm({ day_of_week: 0, start_time: "09:00", end_time: "10:00", subject: "", room: "" });
      load();
    } catch (ex) { toast.error(ex?.response?.data?.detail || "Failed"); }
  };

  const remove = async (id) => {
    try {
      await api.delete(`/timetable/entries/${id}`);
      load();
    } catch (ex) { toast.error(ex?.response?.data?.detail || "Failed"); }
  };

  // Build grid keyed by day
  const byDay = Array.from({ length: 7 }, () => []);
  recurring.forEach((r) => { if (byDay[r.day_of_week]) byDay[r.day_of_week].push(r); });
  byDay.forEach((arr) => arr.sort((a, b) => a.start_time.localeCompare(b.start_time)));

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="timetable-page">
        <header>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A] flex items-center gap-2">
            <CalendarBlank size={14} weight="fill" /> Weekly timetable
          </div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Timetable.</h1>
          <p className="text-[#4A4A4A] mt-3">Recurring weekly schedule pulled from the database. Overrides handled per-date.</p>
        </header>

        <section className="brutal-card p-6 bg-butter" data-testid="timetable-add-form">
          <h2 className="font-display font-bold text-xl mb-3">Add recurring lesson</h2>
          <form onSubmit={add} className="grid sm:grid-cols-2 md:grid-cols-5 gap-3">
            <select className="brutal-input" value={form.day_of_week} onChange={(e) => setForm({ ...form, day_of_week: e.target.value })} data-testid="tt-day">
              {DAY_LABELS.map((d, i) => <option key={d} value={i}>{d}</option>)}
            </select>
            <input className="brutal-input" type="time" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} data-testid="tt-start" />
            <input className="brutal-input" type="time" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} data-testid="tt-end" />
            <input className="brutal-input" placeholder="Subject" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} data-testid="tt-subject" />
            <input className="brutal-input" placeholder="Room" value={form.room} onChange={(e) => setForm({ ...form, room: e.target.value })} data-testid="tt-room" />
            <button className="brutal-btn bg-ink text-white sm:col-span-2 md:col-span-5 inline-flex justify-center items-center gap-2" type="submit" data-testid="tt-add">
              <Plus size={16} weight="bold" /> Add lesson
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
                    <button onClick={() => remove(r.entry_id)} className="mt-1 text-[10px] underline inline-flex items-center gap-1"><Trash size={10} /> Remove</button>
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
