import { Link, useParams } from "react-router-dom";
import AppLayout from "@/components/AppLayout";
import { SUBJECTS, findSubject, subjectsByCategory, SUBJECT_CATEGORIES } from "@/lib/subjects";
import {
  Atom, BookOpen, Bank, Barbell, Function, ArrowLeft, ArrowRight, Sparkle,
  Translate, PaintBrush, MusicNotes, MaskHappy, Code, ForkKnife, Wrench, Brain, UsersThree, Lightbulb, Globe,
} from "@phosphor-icons/react";

const iconMap = {
  Atom, BookOpen, Bank, Barbell, Function, Translate, PaintBrush, MusicNotes,
  MaskHappy, Code, ForkKnife, Wrench, Brain, UsersThree, Lightbulb, Globe,
};

export default function Subjects() {
  const { subjectId } = useParams();
  if (subjectId) return <SubjectDetail subjectId={subjectId} />;
  return <SubjectList />;
}

function SubjectList() {
  const grouped = subjectsByCategory();
  return (
    <AppLayout>
      <div className="max-w-6xl space-y-12">
        <div>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A]">All subjects</div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">What do you want to study?</h1>
          <p className="text-[#4A4A4A] mt-3">{SUBJECTS.length} subjects across {SUBJECT_CATEGORIES.length} categories — from core academics to vocational trades.</p>
        </div>

        {SUBJECT_CATEGORIES.map((cat) => {
          const items = grouped[cat.id] || [];
          if (!items.length) return null;
          return (
            <section key={cat.id}>
              <div className="flex items-baseline gap-3 mb-4 border-b-2 border-ink pb-3">
                <h2 className="font-display font-extrabold text-2xl tracking-tight">{cat.name}</h2>
                <span className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">{items.length}</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {items.map((s) => {
                  const Icon = iconMap[s.icon] || Sparkle;
                  return (
                    <Link
                      key={s.id} to={`/subjects/${s.id}`}
                      className="brutal-card p-5"
                      style={{ backgroundColor: s.accentHex }}
                      data-testid={`subjects-card-${s.id}`}
                    >
                      <div className="flex items-center gap-3 mb-3">
                        <div className="border-2 border-ink bg-white rounded-md p-2 shadow-brutal">
                          <Icon size={20} weight="duotone" />
                        </div>
                        <div className="font-display font-bold text-lg">{s.name}</div>
                      </div>
                      <p className="text-sm text-[#4A4A4A] mb-3">{s.tagline}</p>
                      <div className="text-xs tracking-[0.2em] uppercase font-bold">{s.topics.length} topics →</div>
                    </Link>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>
    </AppLayout>
  );
}

function SubjectDetail({ subjectId }) {
  const subject = findSubject(subjectId);
  if (!subject) {
    return (
      <AppLayout>
        <div className="max-w-3xl">
          <Link to="/subjects" className="text-sm font-bold underline underline-offset-4">← All subjects</Link>
          <h1 className="font-display font-black text-3xl mt-4">Subject not found.</h1>
        </div>
      </AppLayout>
    );
  }
  const Icon = iconMap[subject.icon] || Sparkle;

  return (
    <AppLayout>
      <div className="max-w-6xl space-y-8">
        <Link to="/subjects" className="inline-flex items-center gap-2 text-sm font-bold" data-testid="back-to-subjects">
          <ArrowLeft size={16} weight="bold" /> All subjects
        </Link>

        <div className="brutal-card p-8" style={{ backgroundColor: subject.accentHex }}>
          <div className="flex items-center gap-4 mb-4">
            <div className="border-2 border-ink bg-white rounded-md p-3 shadow-brutal">
              <Icon size={28} weight="duotone" />
            </div>
            <div>
              <div className="text-xs tracking-[0.2em] uppercase font-bold">{subject.topics.length} topics</div>
              <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">{subject.name}</h1>
            </div>
          </div>
          <p className="text-[#4A4A4A] text-lg">{subject.tagline}</p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {subject.topics.map((t) => (
            <Link
              key={t.id}
              to={`/subjects/${subject.id}/topic/${t.id}`}
              className="brutal-card p-6 bg-white"
              data-testid={`topic-card-${t.id}`}
            >
              <div className="font-display font-bold text-xl mb-3">{t.name}</div>
              <ul className="text-sm space-y-1 text-[#4A4A4A]">
                {t.sub.map((s) => <li key={s}>· {s}</li>)}
              </ul>
              <div className="mt-5 inline-flex items-center gap-2 text-xs tracking-[0.2em] uppercase font-bold">
                Open <ArrowRight size={14} weight="bold" />
              </div>
            </Link>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
