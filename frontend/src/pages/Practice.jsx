import { useState } from "react";
import AppLayout from "@/components/AppLayout";
import { Target, ArrowRight, CheckCircle, Calculator, Brain, Lock } from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { canUseCalculator, calcDenyReason } from "@/lib/calcGuard";

const CALC_SETS = [
  { subject: "Maths", topic: "Algebra basics", questions: 12, difficulty: "Foundation", subjectId: "mathematics", topicId: "algebra", calc: true },
  { subject: "Maths", topic: "Arithmetic (calculator)", questions: 10, difficulty: "Foundation", subjectId: "mathematics", topicId: "arithmetic", calc: true },
  { subject: "English", topic: "Grammar & Spelling", questions: 15, difficulty: "Foundation", subjectId: "english", topicId: "grammar", calc: false },
  { subject: "Biology", topic: "Cells & Tissues", questions: 8, difficulty: "Higher", subjectId: "biology", topicId: "cells", calc: false },
];

const MENTAL_SETS = [
  { subject: "Maths", topic: "Mental addition & subtraction", questions: 20, difficulty: "KS1/KS2", subjectId: "mathematics", topicId: "mental-add-sub" },
  { subject: "Maths", topic: "Times tables (2× – 12×)", questions: 24, difficulty: "KS2", subjectId: "mathematics", topicId: "times-tables" },
  { subject: "Maths", topic: "Number bonds to 100", questions: 15, difficulty: "KS1/KS2", subjectId: "mathematics", topicId: "number-bonds" },
  { subject: "Maths", topic: "Fractions of quantities (mental)", questions: 12, difficulty: "KS2", subjectId: "mathematics", topicId: "mental-fractions" },
  { subject: "English", topic: "Grammar & Spelling", questions: 15, difficulty: "KS1/KS2", subjectId: "english", topicId: "grammar" },
  { subject: "Science", topic: "Everyday materials", questions: 10, difficulty: "KS1", subjectId: "science", topicId: "materials" },
];

export default function Practice() {
  const [completed] = useState(new Set());
  const { user } = useAuth();
  const calcAllowed = canUseCalculator(user?.grade_level);
  const sets = calcAllowed ? CALC_SETS : MENTAL_SETS;

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
