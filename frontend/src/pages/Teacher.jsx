import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { SUBJECTS } from "@/lib/subjects";
import { Lightning, Plus, ChartBar, Sparkle, FileText, Warning, ChalkboardTeacher, ArrowsClockwise } from "@phosphor-icons/react";
import { toast } from "sonner";

const TABS = [
  { id: "lessons", label: "Lessons", icon: Lightning },
  { id: "homework", label: "Homework", icon: FileText },
  { id: "detentions", label: "Detentions", icon: Warning },
];

export default function Teacher() {
  const [tab, setTab] = useState("lessons");

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="teacher-page">
        <div className="flex items-center gap-3 mb-2">
          <ChalkboardTeacher size={28} weight="duotone" />
          <div>
            <div className="text-xs tracking-[0.2em] uppercase font-bold text-[#4A4A4A]">Teacher</div>
            <h1 className="font-display font-black text-3xl sm:text-4xl tracking-tight">Your classroom toolkit.</h1>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {TABS.map((t) => (
            <button
              key={t.id} onClick={() => setTab(t.id)}
              data-testid={`teacher-tab-${t.id}`}
              className={`brutal-btn text-sm inline-flex items-center gap-2 ${tab === t.id ? "bg-ink text-white" : "bg-white hover:bg-butter"}`}
            >
              <t.icon size={16} weight="bold" /> {t.label}
            </button>
          ))}
        </div>

        {tab === "lessons" && <LessonsTab />}
        {tab === "homework" && <HomeworkTab />}
        {tab === "detentions" && <DetentionsTab />}
      </div>
    </AppLayout>
  );
}

function LessonsTab() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: "", subject: "Mathematics", year_group: "uk_y10", duration_minutes: 60, objectives: "" });
  const [selected, setSelected] = useState(null);

  const load = async () => {
    try { const { data } = await api.get("/teacher/lessons"); setItems(data.items); } catch {}
  };
  useEffect(() => { load(); }, []);

  const create = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      const { data } = await api.post("/teacher/lessons", { ...form, use_ai: true });
      setItems((it) => [data, ...it]);
      setSelected(data);
      setOpen(false);
      toast.success("Lesson plan generated.");
    } catch (ex) {
      toast.error(ex.response?.data?.detail || "Failed to generate");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-[#4A4A4A] text-sm">Plan a lesson with AI — get a starter, main activities, plenary, and differentiation.</div>
        <button onClick={() => setOpen(true)} data-testid="lesson-new-btn" className="brutal-btn bg-ink text-white inline-flex items-center gap-2">
          <Plus size={16} weight="bold" /> New lesson
        </button>
      </div>

      {open && (
        <form onSubmit={create} className="brutal-card p-6 space-y-3 bg-butter">
          <div className="grid sm:grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Title</span>
              <input data-testid="lesson-title-input" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="Pythagoras' theorem — finding hypotenuse" className="mt-2 brutal-input w-full" />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Subject</span>
              <select data-testid="lesson-subject-select" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })}
                className="mt-2 brutal-input w-full bg-white">
                {SUBJECTS.map((s) => <option key={s.id} value={s.name}>{s.name}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Year group</span>
              <input data-testid="lesson-year-input" value={form.year_group} onChange={(e) => setForm({ ...form, year_group: e.target.value })}
                placeholder="uk_y10" className="mt-2 brutal-input w-full" />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Duration (min)</span>
              <input data-testid="lesson-duration-input" type="number" min={10} value={form.duration_minutes} onChange={(e) => setForm({ ...form, duration_minutes: Number(e.target.value) })}
                className="mt-2 brutal-input w-full" />
            </label>
          </div>
          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Objectives (optional)</span>
            <textarea data-testid="lesson-objectives-input" rows={2} value={form.objectives} onChange={(e) => setForm({ ...form, objectives: e.target.value })}
              className="mt-2 brutal-input w-full" placeholder="Pupils will be able to apply Pythagoras' theorem to right triangles." />
          </label>
          <div className="flex gap-2">
            <button type="button" onClick={() => setOpen(false)} className="brutal-btn bg-white">Cancel</button>
            <button type="submit" disabled={creating} data-testid="lesson-create-btn" className="brutal-btn bg-ink text-white flex-1 inline-flex items-center justify-center gap-2 disabled:opacity-60">
              <Sparkle size={16} weight="bold" /> {creating ? "Generating…" : "Generate lesson plan"}
            </button>
          </div>
        </form>
      )}

      {selected && selected.plan && <LessonPlanView lesson={selected} />}

      <div className="grid md:grid-cols-2 gap-3">
        {items.map((l) => (
          <button key={l.lesson_id} onClick={() => setSelected(l)} className="brutal-card p-4 text-left bg-white" data-testid={`lesson-card-${l.lesson_id}`}>
            <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">{l.subject}</div>
            <div className="font-display font-bold text-lg mt-1">{l.title}</div>
            <div className="text-xs text-[#4A4A4A] mt-1">{l.duration_minutes} min · {new Date(l.created_at).toLocaleDateString()}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

function LessonPlanView({ lesson }) {
  const p = lesson.plan || {};
  return (
    <div className="brutal-card p-6 bg-white" data-testid="lesson-plan-view">
      <h3 className="font-display font-extrabold text-2xl">{p.title || lesson.title}</h3>
      {p.objectives?.length > 0 && (
        <div className="mt-3">
          <div className="text-xs uppercase tracking-[0.2em] font-bold">Learning objectives</div>
          <ul className="list-disc pl-5 mt-1 text-sm space-y-1">
            {p.objectives.map((o, i) => <li key={i}>{o}</li>)}
          </ul>
        </div>
      )}
      {p.starter && (
        <Section title="Starter" duration={p.starter.duration_min}>{p.starter.activity}</Section>
      )}
      {p.main?.length > 0 && (
        <div className="mt-4">
          <div className="text-xs uppercase tracking-[0.2em] font-bold">Main</div>
          <div className="space-y-3 mt-2">
            {p.main.map((m, i) => (
              <div key={i} className="border-2 border-ink rounded-md p-3 bg-butter">
                <div className="text-xs font-bold mb-1">Activity {i + 1} · {m.duration_min} min</div>
                <div className="text-sm">{m.activity}</div>
                {m.teacher_notes && <div className="text-xs text-[#4A4A4A] mt-2"><strong>Notes:</strong> {m.teacher_notes}</div>}
              </div>
            ))}
          </div>
        </div>
      )}
      {p.plenary && (
        <Section title="Plenary" duration={p.plenary.duration_min}>{p.plenary.activity}</Section>
      )}
      {p.differentiation && (
        <div className="mt-4 grid sm:grid-cols-2 gap-3">
          <div className="border-2 border-ink rounded-md p-3 bg-mint">
            <div className="text-xs uppercase tracking-[0.2em] font-bold">Support</div>
            <div className="text-sm mt-1">{p.differentiation.support}</div>
          </div>
          <div className="border-2 border-ink rounded-md p-3 bg-lavender">
            <div className="text-xs uppercase tracking-[0.2em] font-bold">Stretch</div>
            <div className="text-sm mt-1">{p.differentiation.stretch}</div>
          </div>
        </div>
      )}
      {p.success_criteria?.length > 0 && (
        <div className="mt-4">
          <div className="text-xs uppercase tracking-[0.2em] font-bold">Success criteria</div>
          <ul className="list-disc pl-5 mt-1 text-sm space-y-1">
            {p.success_criteria.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>
      )}
      {p.homework && (
        <Section title="Homework">{p.homework}</Section>
      )}
    </div>
  );
}

function Section({ title, duration, children }) {
  return (
    <div className="mt-4">
      <div className="text-xs uppercase tracking-[0.2em] font-bold">{title}{duration > 0 ? ` · ${duration} min` : ""}</div>
      <div className="text-sm mt-1">{children}</div>
    </div>
  );
}

function HomeworkTab() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ title: "", subject: "Mathematics", class_id: "", instructions: "", max_score: 100 });
  const [analysis, setAnalysis] = useState(null);
  const [analyzingId, setAnalyzingId] = useState(null);

  const load = async () => {
    try { const { data } = await api.get("/teacher/homework"); setItems(data.items); } catch {}
  };
  useEffect(() => { load(); }, []);

  const create = async (e) => {
    e.preventDefault();
    try {
      const { data } = await api.post("/teacher/homework", form);
      setItems((it) => [data, ...it]);
      setOpen(false);
      setForm({ title: "", subject: "Mathematics", class_id: "", instructions: "", max_score: 100 });
      toast.success("Homework set.");
    } catch (ex) {
      toast.error(ex.response?.data?.detail || "Failed");
    }
  };

  const analyze = async (id) => {
    setAnalyzingId(id);
    setAnalysis(null);
    try {
      const { data } = await api.post(`/teacher/homework/${id}/analyze`);
      setAnalysis({ id, ...data });
    } catch (ex) {
      toast.error(ex.response?.data?.detail || "Analysis failed");
    } finally {
      setAnalyzingId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-[#4A4A4A] text-sm">Set homework — students submit, AI marks, you get class + per-student insights.</div>
        <button onClick={() => setOpen(true)} data-testid="hw-new-btn" className="brutal-btn bg-ink text-white inline-flex items-center gap-2">
          <Plus size={16} weight="bold" /> Set homework
        </button>
      </div>

      {open && (
        <form onSubmit={create} className="brutal-card p-6 space-y-3 bg-butter">
          <div className="grid sm:grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Title</span>
              <input data-testid="hw-title-input" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="mt-2 brutal-input w-full" />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Subject</span>
              <select data-testid="hw-subject-select" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} className="mt-2 brutal-input w-full bg-white">
                {SUBJECTS.map((s) => <option key={s.id} value={s.name}>{s.name}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Class ID (or name)</span>
              <input data-testid="hw-class-input" required value={form.class_id} onChange={(e) => setForm({ ...form, class_id: e.target.value })} placeholder="8x1" className="mt-2 brutal-input w-full" />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Max score</span>
              <input data-testid="hw-max-input" type="number" min={1} value={form.max_score} onChange={(e) => setForm({ ...form, max_score: Number(e.target.value) })} className="mt-2 brutal-input w-full" />
            </label>
          </div>
          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Instructions / questions</span>
            <textarea data-testid="hw-instructions-input" required rows={4} value={form.instructions} onChange={(e) => setForm({ ...form, instructions: e.target.value })} className="mt-2 brutal-input w-full font-mono text-sm" />
          </label>
          <div className="flex gap-2">
            <button type="button" onClick={() => setOpen(false)} className="brutal-btn bg-white">Cancel</button>
            <button type="submit" data-testid="hw-create-btn" className="brutal-btn bg-ink text-white flex-1">Set homework</button>
          </div>
        </form>
      )}

      <div className="space-y-3">
        {items.map((h) => (
          <div key={h.homework_id} className="brutal-card p-4 bg-white" data-testid={`hw-row-${h.homework_id}`}>
            <div className="flex flex-wrap justify-between gap-3">
              <div>
                <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">{h.subject} · {h.class_id}</div>
                <div className="font-display font-bold text-lg">{h.title}</div>
                <div className="text-xs text-[#4A4A4A] mt-1">Max {h.max_score} · {new Date(h.created_at).toLocaleDateString()}</div>
              </div>
              <button onClick={() => analyze(h.homework_id)} disabled={analyzingId === h.homework_id} data-testid={`hw-analyze-${h.homework_id}`} className="brutal-btn bg-ink text-white inline-flex items-center gap-2 self-start">
                {analyzingId === h.homework_id ? <ArrowsClockwise size={16} className="animate-spin" /> : <ChartBar size={16} weight="bold" />}
                {analyzingId === h.homework_id ? "Analysing…" : "AI analysis"}
              </button>
            </div>
            {analysis?.id === h.homework_id && analysis.analysis && (
              <div className="mt-4 border-t-2 border-ink pt-4 space-y-3" data-testid={`hw-analysis-${h.homework_id}`}>
                <div className="brutal-card p-3 bg-mint text-sm">
                  <strong>Class overview:</strong> {analysis.analysis.class_overview}
                </div>
                <div className="brutal-card p-3 bg-butter text-sm">
                  <strong>Top misconceptions:</strong>
                  <ul className="list-disc pl-5 mt-1">{analysis.analysis.top_misconceptions?.map((m, i) => <li key={i}>{m}</li>)}</ul>
                </div>
                <div className="brutal-card p-3 bg-lavender text-sm">
                  <strong>Recommended next lesson focus:</strong>
                  <ul className="list-disc pl-5 mt-1">{analysis.analysis.recommended_next_lesson?.map((r, i) => <li key={i}>{r}</li>)}</ul>
                </div>
                {analysis.analysis.individual?.length > 0 && (
                  <div>
                    <div className="text-xs uppercase tracking-[0.2em] font-bold mb-2">Per-student analysis</div>
                    <div className="space-y-2">
                      {analysis.analysis.individual.map((s, i) => (
                        <div key={i} className="border-2 border-ink rounded-md p-3 bg-white text-sm">
                          <div className="flex flex-wrap gap-x-4 gap-y-1 items-baseline">
                            <span className="font-bold">{s.student}</span>
                            <span className="text-[#4A4A4A]">Score: {s.score}/{h.max_score}</span>
                            <span className="text-[#4A4A4A]">Expected grade: <strong>{s.expected_grade}</strong></span>
                          </div>
                          <div className="text-xs mt-1"><strong>Strengths:</strong> {s.strengths}</div>
                          <div className="text-xs"><strong>Weaknesses:</strong> {s.weaknesses}</div>
                          <div className="text-xs"><strong>Next steps:</strong> {s.next_steps}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {items.length === 0 && <div className="brutal-card p-6 text-[#4A4A4A]">No homework set yet.</div>}
      </div>
    </div>
  );
}

function DetentionsTab() {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ student_user_id: "", reason: "", date: new Date().toISOString().slice(0, 10), duration_minutes: 30 });

  const load = async () => {
    try { const { data } = await api.get("/teacher/detentions"); setItems(data.items); } catch {}
  };
  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    try {
      await api.post("/teacher/detention", form);
      setForm({ student_user_id: "", reason: "", date: new Date().toISOString().slice(0, 10), duration_minutes: 30 });
      load();
      toast.success("Detention set.");
    } catch (ex) {
      toast.error(ex.response?.data?.detail || "Failed");
    }
  };

  return (
    <div className="space-y-4">
      <form onSubmit={submit} className="brutal-card p-5 bg-butter space-y-3" data-testid="detention-form">
        <h3 className="font-display font-bold text-lg">Set a detention</h3>
        <div className="grid sm:grid-cols-2 gap-3">
          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Student user ID</span>
            <input data-testid="det-student-input" required value={form.student_user_id} onChange={(e) => setForm({ ...form, student_user_id: e.target.value })} className="mt-2 brutal-input w-full" placeholder="user_xxxxx" />
          </label>
          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Date</span>
            <input data-testid="det-date-input" type="date" required value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} className="mt-2 brutal-input w-full" />
          </label>
          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Duration (min)</span>
            <input data-testid="det-duration-input" type="number" min={5} value={form.duration_minutes} onChange={(e) => setForm({ ...form, duration_minutes: Number(e.target.value) })} className="mt-2 brutal-input w-full" />
          </label>
          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Reason</span>
            <input data-testid="det-reason-input" required value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} className="mt-2 brutal-input w-full" placeholder="Disrupting class" />
          </label>
        </div>
        <button type="submit" data-testid="det-create-btn" className="brutal-btn bg-ink text-white">Set detention</button>
      </form>

      <div className="space-y-2">
        {items.map((d) => (
          <div key={d.detention_id} className="brutal-card p-3 bg-white flex justify-between items-center" data-testid={`det-row-${d.detention_id}`}>
            <div>
              <div className="font-bold">Student: {d.student_user_id}</div>
              <div className="text-sm text-[#4A4A4A]">{d.reason} · {d.date} · {d.duration_minutes} min</div>
            </div>
            <span className="px-2 py-0.5 border-2 border-ink rounded-md bg-peach text-xs font-bold uppercase">{d.status}</span>
          </div>
        ))}
        {items.length === 0 && <div className="brutal-card p-6 text-[#4A4A4A]">No detentions logged.</div>}
      </div>
    </div>
  );
}
