import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import AppLayout from "@/components/AppLayout";
import { SUBJECTS, GRADE_LEVELS } from "@/lib/subjects";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Atom, BookOpen, Bank, Barbell, Function, Sparkle, Timer, ArrowRight, Trophy, Clock } from "@phosphor-icons/react";

const iconMap = { Atom, BookOpen, Bank, Barbell, Function };

export default function Dashboard() {
  const { user, refreshUser } = useAuth();
  const [stats, setStats] = useState({ topics_started: 0, topics_completed: 0, focus_sessions_completed: 0, focus_minutes: 0 });
  const [progress, setProgress] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const [s, p] = await Promise.all([api.get("/stats"), api.get("/progress")]);
        setStats(s.data);
        setProgress(p.data.items || []);
      } catch {}
    })();
  }, []);

  const updateGrade = async (grade_level) => {
    await api.patch("/auth/profile", { grade_level });
    await refreshUser();
  };

  const gradeLabel = GRADE_LEVELS.find((g) => g.value === user?.grade_level)?.label || "—";

  return (
    <AppLayout>
      <div className="max-w-6xl space-y-10">
        {/* Header */}
        <div className="flex flex-wrap items-end justify-between gap-4 animate-fade-up">
          <div>
            <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A]">Dashboard</div>
            <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">
              Hello, {user?.name?.split(" ")[0] || "Scholar"}.
            </h1>
            <p className="text-[#4A4A4A] mt-2">Currently studying at <strong className="text-ink">{gradeLabel}</strong> level.</p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <label className="text-xs tracking-[0.2em] uppercase font-bold">Grade</label>
            <select
              data-testid="dashboard-grade-select"
              value={user?.grade_level || "high_school"}
              onChange={(e) => updateGrade(e.target.value)}
              className="brutal-input bg-white py-2"
            >
              {GRADE_LEVELS.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
            </select>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Topics started" value={stats.topics_started} icon={BookOpen} bg="bg-mint" testid="stat-topics-started" />
          <StatCard label="Topics completed" value={stats.topics_completed} icon={Trophy} bg="bg-butter" testid="stat-topics-completed" />
          <StatCard label="Focus sessions" value={stats.focus_sessions_completed} icon={Timer} bg="bg-lavender" testid="stat-focus-sessions" />
          <StatCard label="Focus minutes" value={stats.focus_minutes} icon={Clock} bg="bg-peach" testid="stat-focus-minutes" />
        </div>

        {/* Quick actions */}
        <div className="grid md:grid-cols-3 gap-4">
          <Link to="/subjects" className="brutal-card p-6 bg-mint flex items-center justify-between" data-testid="quick-browse-subjects">
            <div>
              <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2">Browse</div>
              <div className="font-display font-bold text-2xl">All subjects</div>
            </div>
            <ArrowRight size={28} weight="bold" />
          </Link>
          <Link to="/focus" className="brutal-card p-6 bg-peach flex items-center justify-between" data-testid="quick-focus-mode">
            <div>
              <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2">Lock in</div>
              <div className="font-display font-bold text-2xl">Focus Mode</div>
            </div>
            <ArrowRight size={28} weight="bold" />
          </Link>
          <Link to="/progress" className="brutal-card p-6 bg-lavender flex items-center justify-between" data-testid="quick-progress">
            <div>
              <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2">Review</div>
              <div className="font-display font-bold text-2xl">Your progress</div>
            </div>
            <ArrowRight size={28} weight="bold" />
          </Link>
        </div>

        {/* Subject grid */}
        <section>
          <div className="flex items-end justify-between mb-6">
            <h2 className="font-display font-extrabold text-3xl tracking-tight">Pick a subject</h2>
            <Link to="/subjects" className="text-sm font-bold underline underline-offset-4" data-testid="see-all-subjects">See all</Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {SUBJECTS.map((s) => {
              const Icon = iconMap[s.icon] || Sparkle;
              return (
                <Link key={s.id} to={`/subjects/${s.id}`} className="brutal-card p-6" style={{ backgroundColor: s.accentHex }} data-testid={`subject-card-${s.id}`}>
                  <div className="flex items-center gap-3 mb-4">
                    <div className="border-2 border-ink bg-white rounded-md p-2 shadow-brutal">
                      <Icon size={22} weight="duotone" />
                    </div>
                    <div className="font-display font-bold text-xl">{s.name}</div>
                  </div>
                  <p className="text-sm text-[#4A4A4A] mb-4">{s.tagline}</p>
                  <div className="text-xs tracking-[0.2em] uppercase font-bold">{s.topics.length} topics →</div>
                </Link>
              );
            })}
          </div>
        </section>

        {/* Recent progress */}
        {progress.length > 0 && (
          <section>
            <h2 className="font-display font-extrabold text-3xl tracking-tight mb-6">Continue where you left off</h2>
            <div className="grid sm:grid-cols-2 gap-4">
              {progress.slice(0, 4).map((p) => (
                <Link
                  key={p.subject + p.topic}
                  to={`/subjects/${p.subject}/topic/${p.topic}`}
                  className="brutal-card p-5 flex items-center justify-between bg-white"
                  data-testid={`continue-${p.subject}-${p.topic}`}
                >
                  <div>
                    <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A] mb-1">{p.subject}</div>
                    <div className="font-display font-bold text-lg capitalize">{p.topic.replace(/_/g, " ")}</div>
                  </div>
                  <ArrowRight size={20} weight="bold" />
                </Link>
              ))}
            </div>
          </section>
        )}
      </div>
    </AppLayout>
  );
}

function StatCard({ label, value, icon: Icon, bg, testid }) {
  return (
    <div className={`brutal-card p-5 ${bg}`} data-testid={testid}>
      <div className="flex items-center justify-between mb-2">
        <Icon size={22} weight="duotone" />
      </div>
      <div className="font-display font-black text-3xl">{value}</div>
      <div className="text-xs tracking-[0.2em] uppercase font-bold mt-1">{label}</div>
    </div>
  );
}
