import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { Warning, CheckCircle, Trophy, Calendar, GraduationCap } from "@phosphor-icons/react";

const TABS = [
  { id: "grades", label: "Term grade", icon: GraduationCap },
  { id: "detentions", label: "Detentions", icon: Warning },
  { id: "attendance", label: "Attendance", icon: Calendar },
  { id: "achievements", label: "Achievement points", icon: Trophy },
];

export default function MyRecord() {
  const [tab, setTab] = useState("grades");

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="my-record-page">
        <div>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A]">My record</div>
          <h1 className="font-display font-black text-3xl sm:text-4xl tracking-tight">Your school history.</h1>
        </div>

        <div className="flex flex-wrap gap-2">
          {TABS.map((t) => (
            <button key={t.id} onClick={() => setTab(t.id)} data-testid={`mr-tab-${t.id}`}
              className={`brutal-btn text-sm inline-flex items-center gap-2 ${tab === t.id ? "bg-ink text-white" : "bg-white hover:bg-butter"}`}>
              <t.icon size={16} weight="bold" /> {t.label}
            </button>
          ))}
        </div>

        {tab === "grades" && <GradesTab />}
        {tab === "detentions" && <DetentionsTab />}
        {tab === "attendance" && <AttendanceTab />}
        {tab === "achievements" && <AchievementsTab />}
      </div>
    </AppLayout>
  );
}

function GradesTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.get("/student/term-grade")
      .then(({ data }) => setData(data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);
  if (loading) return <div className="brutal-card p-6 text-[#4A4A4A]">Loading term grade…</div>;
  if (!data || data.percentage === null) {
    return <Empty msg="No graded assignments yet. Ask your teacher to promote a homework to an assignment." />;
  }
  const gradeBg = data.percentage >= 70 ? "bg-mint" : data.percentage >= 50 ? "bg-butter" : "bg-peach";
  return (
    <div className="space-y-4" data-testid="my-grades">
      <div className={`brutal-card p-6 ${gradeBg}`}>
        <div className="text-xs uppercase tracking-[0.2em] font-bold">Weighted term grade</div>
        <div className="flex items-baseline gap-3 mt-1">
          <div className="font-display font-black text-5xl" data-testid="my-grade-percentage">{data.percentage}%</div>
          <div className="text-2xl font-display font-bold" data-testid="my-grade-band">Band {data.band}</div>
        </div>
        <div className="text-sm mt-2 text-[#4A4A4A]">
          Across {data.count} assignment{data.count === 1 ? "" : "s"} · GCSE 9-1 estimated band using each assignment's weight.
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-xs uppercase tracking-[0.2em] font-bold">Assignment breakdown</div>
        {data.assignments.map((a) => (
          <div key={a.homework_id} className="brutal-card p-3 bg-white flex flex-wrap items-center gap-3" data-testid={`my-grade-row-${a.homework_id}`}>
            <div className="flex-1 min-w-[220px]">
              <div className="font-bold">{a.title}</div>
              <div className="text-xs text-[#4A4A4A]">{a.subject}{a.due_date ? ` · due ${new Date(a.due_date).toLocaleDateString()}` : ""}</div>
            </div>
            <div className="text-xs font-mono px-2 py-0.5 border-2 border-ink rounded-md bg-butter">
              {a.score}/{a.max_score} · {a.percentage}%
            </div>
            <div className="text-xs font-mono text-[#4A4A4A]">weight ×{a.weight}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DetentionsTab() {
  const [items, setItems] = useState([]);
  useEffect(() => { api.get("/student/my-detentions").then(({ data }) => setItems(data.items)).catch(() => {}); }, []);
  if (items.length === 0) return <Empty msg="No detentions on your record. Keep it up." good />;
  return (
    <div className="space-y-2" data-testid="my-detentions">
      {items.map((d) => (
        <div key={d.detention_id} className="brutal-card p-4 bg-white flex justify-between items-center">
          <div>
            <div className="font-bold">{d.reason}</div>
            <div className="text-sm text-[#4A4A4A]">{d.date} · {d.duration_minutes} min · set by {d.set_by_name}</div>
          </div>
          <span className="px-2 py-0.5 border-2 border-ink rounded-md bg-peach text-xs font-bold uppercase">{d.status}</span>
        </div>
      ))}
    </div>
  );
}

function AttendanceTab() {
  const [data, setData] = useState({ items: [], rate: 100, total: 0, present: 0 });
  useEffect(() => { api.get("/student/my-attendance").then(({ data }) => setData(data)).catch(() => {}); }, []);
  return (
    <div className="space-y-4" data-testid="my-attendance">
      <div className="brutal-card p-6 bg-mint">
        <div className="text-xs uppercase tracking-[0.2em] font-bold">Attendance rate</div>
        <div className="font-display font-black text-5xl mt-1">{data.rate.toFixed(1)}%</div>
        <div className="text-sm mt-1">{data.present} of {data.total} marked</div>
      </div>
      {data.items.length === 0 ? <Empty msg="No attendance logged yet." />
        : (
          <div className="space-y-2">
            {data.items.slice(0, 30).map((a, i) => (
              <div key={i} className="brutal-card p-3 bg-white flex justify-between items-center">
                <div className="text-sm">{a.date} · class {a.class_id}</div>
                <span className={`px-2 py-0.5 border-2 border-ink rounded-md text-xs font-bold uppercase ${a.status === "present" ? "bg-mint" : a.status === "late" ? "bg-butter" : "bg-peach"}`}>{a.status}</span>
              </div>
            ))}
          </div>
        )}
    </div>
  );
}

function AchievementsTab() {
  const [data, setData] = useState({ items: [], total_points: 0 });
  useEffect(() => { api.get("/student/my-achievements").then(({ data }) => setData(data)).catch(() => {}); }, []);
  return (
    <div className="space-y-4" data-testid="my-achievements">
      <div className="brutal-card p-6 bg-butter">
        <div className="text-xs uppercase tracking-[0.2em] font-bold">Achievement points</div>
        <div className="font-display font-black text-5xl mt-1">{data.total_points}</div>
      </div>
      {data.items.length === 0 ? <Empty msg="No achievement points yet — keep going." />
        : (
          <div className="space-y-2">
            {data.items.map((a) => (
              <div key={a.achievement_id} className="brutal-card p-3 bg-white flex justify-between items-center">
                <div>
                  <div className="font-bold">{a.reason}</div>
                  <div className="text-xs text-[#4A4A4A]">awarded by {a.awarded_by_name} · {new Date(a.created_at).toLocaleDateString()}</div>
                </div>
                <div className="font-display font-black text-2xl">+{a.points}</div>
              </div>
            ))}
          </div>
        )}
    </div>
  );
}

function Empty({ msg, good = false }) {
  return (
    <div className={`brutal-card p-6 text-center ${good ? "bg-mint" : ""}`}>
      {good && <CheckCircle size={28} weight="duotone" className="mx-auto mb-2" />}
      <div className="text-[#4A4A4A]">{msg}</div>
    </div>
  );
}
