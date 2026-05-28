import { Link } from "react-router-dom";
import GlobalNav from "@/components/GlobalNav";
import { GraduationCap, Atom, BookOpen, Bank, Barbell, Function, Sparkle, Timer, CheckCircle, ArrowRight, Question } from "@phosphor-icons/react";

const SUBJECT_TILES = [
  { name: "Mathematics", color: "#E6F7EB", icon: Function },
  { name: "English", color: "#EBE6F7", icon: BookOpen },
  { name: "Science", color: "#E6F7EB", icon: Atom },
  { name: "History", color: "#EBE6F7", icon: Bank },
  { name: "PE", color: "#FFD8D1", icon: Barbell },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-paper text-ink">
      <GlobalNav />

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-6 pt-16 pb-20 grid md:grid-cols-2 gap-12 items-center">
        <div className="space-y-8 animate-fade-up">
          <span className="inline-block px-3 py-1 border-2 border-ink rounded-full bg-butter text-xs tracking-[0.2em] uppercase font-bold shadow-brutal">
            Preschool → PhD
          </span>
          <h1 className="font-display font-black text-5xl sm:text-6xl lg:text-7xl tracking-tight leading-[0.95]">
            A focused
            <br />
            <span className="bg-mint border-2 border-ink px-3 inline-block shadow-brutal">study hub</span>
            <br />
            for every level.
          </h1>
          <p className="text-lg leading-relaxed max-w-xl text-[#4A4A4A]">
            AI-generated revision summaries, quizzes, and flashcards across Math, English, Science, History and PE — paired with a no-escape Focus Mode that keeps you on task.
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            <Link to="/register" className="brutal-btn bg-ink text-white text-base inline-flex items-center gap-2" data-testid="hero-cta-start">
              Start learning <ArrowRight size={18} weight="bold" />
            </Link>
            <Link to="/login" className="brutal-btn bg-white hover:bg-butter text-base inline-flex items-center gap-2" data-testid="hero-cta-signin">
              I already have an account
            </Link>
          </div>
          <div className="flex flex-wrap gap-6 pt-4 text-sm">
            <div className="flex items-center gap-2"><CheckCircle size={18} weight="fill" /> No ads</div>
            <div className="flex items-center gap-2"><CheckCircle size={18} weight="fill" /> Offline-friendly</div>
            <div className="flex items-center gap-2"><CheckCircle size={18} weight="fill" /> AI tutor included</div>
          </div>
        </div>

        <div className="relative">
          <div className="brutal-card p-3 rotate-1">
            <img
              src="https://static.prod-images.emergentagent.com/jobs/0e72f85f-e4b0-46dd-a92f-27b937d72463/images/ece9de530abfeb52ba1d5a3daea3272538a3150bc1336cb02f1243a7e7a66590.png"
              alt="Books"
              className="w-full h-auto rounded-md"
            />
          </div>
          <div className="absolute -bottom-6 -left-6 brutal-card bg-butter p-4 max-w-[230px] -rotate-3" data-testid="hero-stats-card">
            <div className="text-xs uppercase tracking-[0.2em] font-bold">Focus this week</div>
            <div className="font-display font-black text-4xl mt-1">12h 40m</div>
            <div className="text-xs mt-1 text-[#4A4A4A]">across 17 sessions</div>
          </div>
        </div>
      </section>

      {/* Subjects */}
      <section className="bg-white border-y-2 border-ink">
        <div className="max-w-7xl mx-auto px-6 py-20">
          <div className="flex items-end justify-between mb-10 flex-wrap gap-4">
            <div>
              <div className="text-xs tracking-[0.2em] uppercase font-bold mb-3">5 Subjects</div>
              <h2 className="font-display font-extrabold text-4xl sm:text-5xl tracking-tight">All the essentials, none of the fluff.</h2>
            </div>
            <p className="max-w-md text-[#4A4A4A]">Each topic is generated on demand at your exact grade level — from preschool to PhD.</p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {SUBJECT_TILES.map((s) => (
              <div
                key={s.name}
                className="brutal-card p-6 flex flex-col items-start gap-4"
                style={{ backgroundColor: s.color }}
                data-testid={`subject-tile-${s.name.toLowerCase()}`}
              >
                <div className="border-2 border-ink bg-white rounded-md p-2 shadow-brutal">
                  <s.icon size={26} weight="duotone" />
                </div>
                <div className="font-display font-bold text-xl">{s.name}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-6 py-20 grid md:grid-cols-3 gap-6">
        <div className="brutal-card p-8 bg-mint">
          <Sparkle size={28} weight="duotone" />
          <h3 className="font-display font-bold text-2xl mt-4 mb-2">AI study packs</h3>
          <p className="text-[#4A4A4A]">Summaries, MCQs, flashcards and worked examples generated in seconds for any topic.</p>
        </div>
        <div className="brutal-card p-8 bg-lavender">
          <BookOpen size={28} weight="duotone" />
          <h3 className="font-display font-bold text-2xl mt-4 mb-2">Personal tutor chat</h3>
          <p className="text-[#4A4A4A]">Stuck? Ask a question, get a clear answer at your level — never condescending, never vague.</p>
        </div>
        <div className="brutal-card p-8 bg-peach">
          <Timer size={28} weight="duotone" />
          <h3 className="font-display font-bold text-2xl mt-4 mb-2">Focus Mode</h3>
          <p className="text-[#4A4A4A]">Lock yourself into a single task for X minutes. No tab-switching escape route.</p>
        </div>
      </section>

      {/* Homework Helper teaser */}
      <section className="bg-white border-y-2 border-ink">
        <div className="max-w-7xl mx-auto px-6 py-16 grid md:grid-cols-2 gap-10 items-center">
          <div>
            <div className="text-xs tracking-[0.2em] uppercase font-bold mb-3">New · Homework Helper</div>
            <h2 className="font-display font-extrabold text-4xl sm:text-5xl tracking-tight mb-4">Stuck on a Sparx problem?</h2>
            <p className="text-[#4A4A4A] text-lg mb-6 max-w-lg">
              Paste any question from Sparx Maths, MyMaths, Seneca, a textbook or worksheet. We'll ask what you don't understand — then walk you through it step-by-step. Not just the answer.
            </p>
            <Link to="/help" className="brutal-btn bg-ink text-white inline-flex items-center gap-2" data-testid="landing-help-cta">
              <Question size={18} weight="bold" /> Try Homework Helper
            </Link>
          </div>
          <div className="brutal-card p-6 bg-butter">
            <div className="text-xs uppercase tracking-[0.2em] font-bold mb-3">Example session</div>
            <div className="space-y-3 text-sm">
              <div className="border-2 border-ink rounded-md p-3 bg-white"><strong>You:</strong> Solve 2(x − 3) = 14</div>
              <div className="border-2 border-ink rounded-md p-3 bg-mint"><strong>ScholarHub:</strong> Got it. Where are you stuck — distributing the 2, isolating x, or checking the answer?</div>
              <div className="border-2 border-ink rounded-md p-3 bg-white"><strong>You:</strong> Distributing</div>
              <div className="border-2 border-ink rounded-md p-3 bg-mint"><strong>ScholarHub:</strong> Multiply 2 by both terms inside the bracket: 2·x = 2x, and 2·(−3) = −6. So 2(x−3) = 2x − 6 ...</div>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t-2 border-ink py-10 text-center text-sm text-[#4A4A4A]">
        Built for serious learners. © {new Date().getFullYear()} ScholarHub.
      </footer>
    </div>
  );
}
