import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { Target, ArrowRight, CheckCircle, Calculator, Brain, Lock, Flame, Sparkle } from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { canUseCalculator, calcDenyReason } from "@/lib/calcGuard";
import { toast } from "sonner";

const CALC_SETS = [
  { subject: "Maths", topic: "Algebra basics", questions: 12, difficulty: "Foundation", subjectId: "mathematics", topicId: "algebra", calc: true },
  { subject: "Maths", topic: "Arithmetic (calculator)", questions: 10, difficulty: "Foundation", subjectId: "mathematics", topicId: "arithmetic", calc: true },
  { subject: "English", topic: "Grammar & Spelling", questions: 15, difficulty: "Foundation", subjectId: "english", topicId: "grammar", calc: false },
  { subject: "Biology", topic: "Cells & Tissues", questions: 8, difficulty: "Higher", subjectId: "biology", topicId: "cells", calc: false },
];

const MENTAL_SETS = [
  { subject: "Maths", topic: "Mental addition & subtraction", questions: 20, difficulty: "KS1/KS2", subjectId: "mathematics", topicId: "mental-add-sub", mental: true },
  { subject: "Maths", topic: "Times tables (2× – 12×)", questions: 24, difficulty: "KS2", subjectId: "mathematics", topicId: "times-tables", mental: true },
  { subject: "Maths", topic: "Number bonds to 100", questions: 15, difficulty: "KS1/KS2", subjectId: "mathematics", topicId: "number-bonds", mental: true },
  { subject: "Maths", topic: "Fractions of quantities (mental)", questions: 12, difficulty: "KS2", subjectId: "mathematics", topicId: "mental-fractions", mental: true },
  { subject: "English", topic: "Grammar & Spelling", questions: 15, difficulty: "KS1/KS2", subjectId: "english", topicId: "grammar" },
  { subject: "Science", topic: "Everyday materials", questions: 10, difficulty: "KS1", subjectId: "science", topicId: "materials" },
];

const WEEKDAY = ["S", "M", "T", "W", "T", "F", "S"];

export default function Practice() {
  const [completed] = useState(new Set());
  const { user } = useAuth();
  const calcAllowed = canUseCalculator(user?.grade_level);
  const sets = calcAllowed ? CALC_SETS : MENTAL_SETS;
  const [streak, setStreak] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (calcAllowed) return;
    api.get("/practice/mental-streak").then(({ data }) => setStreak(data)).catch(() => setStreak(null));
  }, [calcAllowed]);

  const logDrill = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const { data } = await api.post("/practice/mental-maths/complete");
      // refresh 7-day heatmap after the streak bump
      const { data: fresh } = await api.get("/practice/mental-streak");
      setStreak(fresh);
      if (data.already_done_today) {
        toast.success(`Nice — already ticked off today. Streak: ${data.current_streak} 🔥`);
      } else {
        toast.success(`Streak +1 → ${data.current_streak} day${data.current_streak === 1 ? "" : "s"} 🔥`);
      }
    } catch (ex) {
      toast.error(ex.response?.data?.detail || "Couldn't record your drill");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppLayout>
      <div className="space-y-6" data-testid="practice-page">
        <header>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A] flex items-center gap-2">
            <Target size={14} weight="fill" /> Practice
          </div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Practice.</h1>
          <p className="text-[#4A4A4A] mt-3">Short, focused drills. Ten minutes a day beats a two-hour cram.</p>
        </header>

        {!calcAllowed && (
          <div className="brutal-card p-4 bg-butter flex items-start gap-3" data-testid="calc-guard-banner">
            <Lock size={20} weight="fill" className="shrink-0 mt-0.5" />
            <div className="text-sm">
              <div className="font-display font-bold text-base flex items-center gap-2">
                <Brain size={16} weight="bold" /> Mental-methods mode
              </div>
              <p className="mt-1">{calcDenyReason()} We're showing you drills that build fluency without a calculator.</p>
            </div>
          </div>
        )}

        {!calcAllowed && streak && (
          <div className="brutal-card p-5 bg-peach" data-testid="mental-streak-card">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <Flame size={44} weight="fill" className="text-red-700" />
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">Mental-maths streak</div>
                  <div className="font-display font-black text-4xl mt-1" data-testid="mental-streak-current">
                    {streak.current_streak} <span className="text-lg font-bold">day{streak.current_streak === 1 ? "" : "s"} 🔥</span>
                  </div>
                  <div className="text-xs text-[#4A4A4A]">Best: {streak.best_streak} · Total drills: {streak.total_completions}</div>
                </div>
              </div>
              <button onClick={logDrill} disabled={busy} data-testid="mental-streak-log-btn"
                className="brutal-btn bg-ink text-white inline-flex items-center gap-2 disabled:opacity-60">
                <Sparkle size={16} weight="bold" /> {busy ? "Saving…" : (streak.last_completed_date === new Date().toISOString().slice(0,10) ? "Done today ✓" : "I did a drill today")}
              </button>
            </div>
            <div className="mt-4 flex items-center gap-2" data-testid="mental-streak-heatmap">
              {(streak.last_7_days || []).map((d, i) => (
                <div key={d.date} className={`w-9 h-9 rounded-md border-2 border-ink flex items-center justify-center text-xs font-bold ${d.done ? "bg-mint" : "bg-white text-[#4A4A4A]"}`} title={d.date}>
                  {WEEKDAY[new Date(d.date).getDay()]}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-3">
          {sets.filter((p) => calcAllowed || !p.calc).map((p) => (
            <Link
              key={`${p.subject}-${p.topic}`}
              to={`/subjects/${p.subjectId}/topic/${p.topicId}`}
              className="brutal-card p-5 bg-white hover:bg-mint transition-colors"
              data-testid={`practice-${p.subjectId}-${p.topicId}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A] flex items-center gap-2">
                    {p.subject}
                    {calcAllowed && p.calc && <Calculator size={12} weight="bold" />}
                    {!calcAllowed && <Brain size={12} weight="bold" />}
                  </div>
                  <h3 className="font-display font-bold text-lg mt-1">{p.topic}</h3>
                  <p className="text-xs text-[#4A4A4A] mt-1">{p.questions} questions · {p.difficulty}</p>
                </div>
                {completed.has(p.topic) ? <CheckCircle size={22} weight="fill" className="text-green-700" /> : <ArrowRight size={20} />}
              </div>
            </Link>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
