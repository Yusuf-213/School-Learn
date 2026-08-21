import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { ClipboardText, Robot, Calendar, ArrowRight } from "@phosphor-icons/react";
import { Link } from "react-router-dom";

const DEMO_TASKS = [
  { subject: "Maths", title: "Exercise 4.3 – solving linear equations", due: "Tue 21 Feb", status: "todo" },
  { subject: "English", title: "Read chapters 3–5 of An Inspector Calls", due: "Wed 22 Feb", status: "todo" },
  { subject: "Science", title: "Diagram: parts of the plant cell", due: "Thu 23 Feb", status: "done" },
  { subject: "History", title: "Source questions on the Norman Conquest", due: "Fri 24 Feb", status: "todo" },
];

export default function Homework() {
  const { user } = useAuth();
  const [tasks, setTasks] = useState(DEMO_TASKS);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Best-effort: pull real homework if the endpoint exists, otherwise show demo tasks
    api.get("/homework/mine").then(({ data }) => {
      if (data?.items?.length) {
        setTasks(data.items);
      }
    }).catch(() => {}).finally(() => setLoading(false));
  }, [user]);

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="homework-page">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A] flex items-center gap-2">
              <ClipboardText size={14} weight="fill" /> Homework
            </div>
            <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Homework.</h1>
            <p className="text-[#4A4A4A] mt-3">All your set tasks in one place — plus an AI tutor when you get stuck.</p>
          </div>
          <Link to="/help" className="brutal-btn bg-mint hover:bg-white inline-flex items-center gap-2" data-testid="homework-ai-help">
            <Robot size={16} weight="bold" /> Get AI help
          </Link>
        </header>

        <div className="grid md:grid-cols-4 gap-3">
          <Stat label="Total" value={tasks.length} bg="bg-butter" />
          <Stat label="To do" value={tasks.filter(t => t.status !== "done").length} bg="bg-peach" />
          <Stat label="Done" value={tasks.filter(t => t.status === "done").length} bg="bg-mint" />
          <Stat label="This week" value={tasks.length} bg="bg-white" />
        </div>

        <section>
          <h2 className="font-display font-extrabold text-2xl mb-3">Set tasks</h2>
          {loading ? (
            <div className="brutal-card p-6 text-[#4A4A4A]">Loading…</div>
          ) : (
            <div className="space-y-2">
              {tasks.map((t, i) => (
                <div key={i} className={`brutal-card p-4 flex flex-wrap justify-between items-center gap-3 ${t.status === "done" ? "bg-mint" : "bg-white"}`} data-testid={`homework-task-${i}`}>
                  <div>
                    <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">{t.subject}</div>
                    <div className={`font-bold ${t.status === "done" ? "line-through opacity-70" : ""}`}>{t.title}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm inline-flex items-center gap-1 text-[#4A4A4A]">
                      <Calendar size={14} /> {t.due}
                    </span>
                    <Link to="/help" className="brutal-btn bg-butter hover:bg-white text-xs inline-flex items-center gap-1">
                      Ask AI <ArrowRight size={12} weight="bold" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </AppLayout>
  );
}

function Stat({ label, value, bg }) {
  return (
    <div className={`brutal-card p-4 ${bg}`}>
      <div className="font-display font-black text-2xl">{value}</div>
      <div className="text-xs tracking-[0.2em] uppercase font-bold mt-1">{label}</div>
    </div>
  );
}
