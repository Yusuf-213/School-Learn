import { useState } from "react";
import AppLayout from "@/components/AppLayout";
import { Target, ArrowRight, CheckCircle } from "@phosphor-icons/react";
import { Link } from "react-router-dom";

const PRACTICE_SETS = [
  { subject: "Maths", topic: "Algebra basics", questions: 12, difficulty: "Foundation", subjectId: "mathematics", topicId: "algebra" },
  { subject: "Maths", topic: "Arithmetic", questions: 10, difficulty: "Foundation", subjectId: "mathematics", topicId: "arithmetic" },
  { subject: "English", topic: "Grammar & Spelling", questions: 15, difficulty: "Foundation", subjectId: "english", topicId: "grammar" },
  { subject: "Biology", topic: "Cells & Tissues", questions: 8, difficulty: "Higher", subjectId: "biology", topicId: "cells" },
];

export default function Practice() {
  const [completed] = useState(new Set());
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

        <div className="grid md:grid-cols-2 gap-3">
          {PRACTICE_SETS.map((p) => (
            <Link
              key={`${p.subject}-${p.topic}`}
              to={`/subjects/${p.subjectId}/topic/${p.topicId}`}
              className="brutal-card p-5 bg-white hover:bg-mint transition-colors"
              data-testid={`practice-${p.subjectId}-${p.topicId}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">{p.subject}</div>
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
