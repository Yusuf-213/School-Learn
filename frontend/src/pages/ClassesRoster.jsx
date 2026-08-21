import { useCallback, useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Users, ChalkboardTeacher, Plus, X, GraduationCap } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function ClassesRoster() {
  const { user } = useAuth();
  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [teacherInput, setTeacherInput] = useState("");
  const [studentInput, setStudentInput] = useState("");
  const [newClass, setNewClass] = useState({ name: "", year_group: "", subject: "" });

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/school/classes");
      setClasses(data.classes || []);
      setSelected((prev) => prev || data.classes?.[0] || null);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not load classes");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const reselect = async (cid) => {
    const { data } = await api.get(`/school/classes/${cid}`);
    setSelected(data);
  };

  const createClass = async (e) => {
    e.preventDefault();
    if (!newClass.name.trim()) return;
    try {
      const { data } = await api.post("/school/classes", newClass);
      setNewClass({ name: "", year_group: "", subject: "" });
      toast.success(`Class ${data.name} created`);
      await load();
      await reselect(data.class_id);
    } catch (ex) {
      toast.error(ex?.response?.data?.detail || "Failed to create class");
    }
  };

  const addRoster = async (kind) => {
    if (!selected) return;
    const raw = kind === "teacher" ? teacherInput : studentInput;
    const emails = raw.split(/[,;\s]+/).map((s) => s.trim()).filter(Boolean);
    if (!emails.length) return;
    try {
      const { data } = await api.post(`/school/classes/${selected.class_id}/${kind}s`, { emails });
      setSelected(data);
      if (kind === "teacher") setTeacherInput(""); else setStudentInput("");
      await load();
      toast.success(`${emails.length} ${kind}${emails.length > 1 ? "s" : ""} added`);
    } catch (ex) {
      toast.error(ex?.response?.data?.detail || "Failed to add");
    }
  };

  const removeFrom = async (kind, email) => {
    if (!selected) return;
    try {
      const { data } = await api.request({
        method: "DELETE",
        url: `/school/classes/${selected.class_id}/${kind}s`,
        data: { email },
      });
      setSelected(data);
      await load();
    } catch (ex) {
      toast.error(ex?.response?.data?.detail || "Failed to remove");
    }
  };

  const canManage = user?.role === "owner" || user?.role === "school_admin" || user?.role === "teacher";

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="classes-page">
        <header>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A] flex items-center gap-2">
            <GraduationCap size={14} weight="fill" /> Class roster
          </div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Classes.</h1>
          <p className="text-[#4A4A4A] mt-3">Add or remove teachers and students per form group in seconds.</p>
        </header>

        <div className="grid md:grid-cols-3 gap-4">
          <aside className="brutal-card p-4 bg-white md:sticky md:top-4 md:max-h-[calc(100vh-4rem)] md:overflow-y-auto">
            <h2 className="font-display font-bold text-lg mb-3">Groups</h2>
            {loading ? (
              <div className="text-sm text-[#4A4A4A]">Loading…</div>
            ) : classes.length === 0 ? (
              <div className="text-sm text-[#4A4A4A]" data-testid="classes-empty">No classes yet — create one below.</div>
            ) : (
              <ul className="space-y-1">
                {classes.map((c) => (
                  <li key={c.class_id}>
                    <button
                      onClick={() => reselect(c.class_id)}
                      data-testid={`class-row-${c.class_id}`}
                      className={`w-full text-left px-3 py-2 rounded-md border-2 border-ink text-sm font-bold flex justify-between items-center gap-2
                        ${selected?.class_id === c.class_id ? "bg-mint" : "bg-white hover:bg-butter"}`}
                    >
                      <span className="flex-1 min-w-0 truncate">
                        {c.name}
                        {c.school_name && user?.role === "owner" && (
                          <span className="ml-2 text-[10px] uppercase tracking-widest text-[#4A4A4A] font-mono truncate">
                            &nbsp;· {c.school_name}
                          </span>
                        )}
                      </span>
                      <span className="text-xs font-mono text-[#4A4A4A] whitespace-nowrap">{c.teacher_count}T · {c.student_count}S</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {canManage && (
              <form onSubmit={createClass} className="mt-4 border-t-2 border-ink pt-4 space-y-2" data-testid="class-create-form">
                <h3 className="text-xs uppercase tracking-[0.2em] font-bold">New class</h3>
                <input required data-testid="class-name-input" value={newClass.name}
                  onChange={(e) => setNewClass({ ...newClass, name: e.target.value })}
                  placeholder="e.g. 9C" className="brutal-input w-full text-sm" />
                <input data-testid="class-year-input" value={newClass.year_group}
                  onChange={(e) => setNewClass({ ...newClass, year_group: e.target.value })}
                  placeholder="Year group (e.g. Y9)" className="brutal-input w-full text-sm" />
                <input data-testid="class-subject-input" value={newClass.subject}
                  onChange={(e) => setNewClass({ ...newClass, subject: e.target.value })}
                  placeholder="Subject (optional)" className="brutal-input w-full text-sm" />
                <button type="submit" className="brutal-btn bg-ink text-white w-full inline-flex justify-center items-center gap-2" data-testid="class-create-btn">
                  <Plus size={16} weight="bold" /> Add class
                </button>
              </form>
            )}
          </aside>

          <section className="md:col-span-2 space-y-4">
            {!selected ? (
              <div className="brutal-card p-8 text-center text-[#4A4A4A]">Pick a class on the left to manage its roster.</div>
            ) : (
              <>
                <div className="brutal-card p-6 bg-butter">
                  <div className="flex justify-between items-start gap-3 flex-wrap">
                    <div>
                      <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">Class</div>
                      <h2 className="font-display font-black text-3xl">{selected.name}</h2>
                      <div className="text-xs text-[#4A4A4A] mt-1">
                        {selected.year_group ? `Year ${selected.year_group.replace(/^y/i, "")} · ` : ""}
                        {selected.subject || "General"}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">Roster</div>
                      <div className="font-display font-bold text-lg">{(selected.teacher_emails || []).length}T · {(selected.student_emails || []).length}S</div>
                    </div>
                  </div>
                </div>

                <RosterPanel
                  title="Teachers"
                  icon={ChalkboardTeacher}
                  bg="bg-mint"
                  emails={selected.teacher_emails || []}
                  input={teacherInput}
                  onInput={setTeacherInput}
                  onAdd={() => addRoster("teacher")}
                  onRemove={(e) => removeFrom("teacher", e)}
                  testid="teachers"
                />

                <RosterPanel
                  title="Students"
                  icon={Users}
                  bg="bg-lavender"
                  emails={selected.student_emails || []}
                  input={studentInput}
                  onInput={setStudentInput}
                  onAdd={() => addRoster("student")}
                  onRemove={(e) => removeFrom("student", e)}
                  testid="students"
                />
              </>
            )}
          </section>
        </div>
      </div>
    </AppLayout>
  );
}

function RosterPanel({ title, icon: Icon, bg, emails, input, onInput, onAdd, onRemove, testid }) {
  return (
    <section className={`brutal-card p-6 ${bg}`} data-testid={`roster-${testid}`}>
      <div className="flex items-center gap-2 mb-3">
        <Icon size={18} weight="bold" />
        <h3 className="font-display font-bold text-xl">{title} ({emails.length})</h3>
      </div>
      <div className="flex gap-2 mb-3 flex-wrap">
        <input
          type="text"
          value={input}
          onChange={(e) => onInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); onAdd(); } }}
          placeholder="email1@school.uk, email2@school.uk"
          className="brutal-input flex-1 min-w-[220px] text-sm"
          data-testid={`roster-${testid}-input`}
        />
        <button
          onClick={onAdd}
          className="brutal-btn bg-white hover:bg-butter text-sm inline-flex items-center gap-1"
          data-testid={`roster-${testid}-add`}
        >
          <Plus size={14} weight="bold" /> Add
        </button>
      </div>
      {emails.length === 0 ? (
        <p className="text-sm text-[#4A4A4A]">No {title.toLowerCase()} yet. Paste one or many emails separated by commas.</p>
      ) : (
        <ul className="space-y-1">
          {emails.map((e) => (
            <li key={e} className="flex justify-between items-center bg-white border-2 border-ink rounded-md px-3 py-1.5 text-sm font-mono" data-testid={`roster-${testid}-${e}`}>
              <span>{e}</span>
              <button onClick={() => onRemove(e)} className="text-red-800 hover:text-red-600" aria-label={`Remove ${e}`} data-testid={`roster-${testid}-remove-${e}`}>
                <X size={14} weight="bold" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
