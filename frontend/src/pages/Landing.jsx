import { Link } from "react-router-dom";
import GlobalNav from "@/components/GlobalNav";
import { Atom, BookOpen, Bank, Barbell, Function, Sparkle, Timer, CheckCircle, ArrowRight, Question, ChalkboardTeacher, Compass, Trophy, ChartLineUp } from "@phosphor-icons/react";

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
            Preschool → University
          </span>
          <h1 className="font-display font-black text-5xl sm:text-6xl lg:text-7xl tracking-tight leading-[0.95]">
            One platform.
            <br />
            <span className="bg-mint border-2 border-ink px-3 inline-block shadow-brutal">Learnify</span>
            <br />
            replaces them all.
          </h1>
          <p className="text-lg leading-relaxed max-w-xl text-[#4A4A4A]">
            Built ground-up for schools — AI lesson planner, homework with class + per-student analysis and expected grades, register, detentions, achievement points, and a Dreams page that maps the route from "what I want to be" to "how to get there".
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            <Link to="/signup/school" className="brutal-btn bg-ink text-white text-base inline-flex items-center gap-2" data-testid="hero-cta-school">
              Register your school <ArrowRight size={18} weight="bold" />
            </Link>
            <Link to="/register" className="brutal-btn bg-white hover:bg-butter text-base inline-flex items-center gap-2" data-testid="hero-cta-individual">
              I'm a student
            </Link>
          </div>
          <div className="flex flex-wrap gap-6 pt-4 text-sm">
            <div className="flex items-center gap-2"><CheckCircle size={18} weight="fill" /> Built for UK schools</div>
            <div className="flex items-center gap-2"><CheckCircle size={18} weight="fill" /> AI lesson planner</div>
            <div className="flex items-center gap-2"><CheckCircle size={18} weight="fill" /> One annual price</div>
          </div>
        </div>

        <div className="relative">
          <div className="brutal-card p-3 rotate-1">
            <img src="https://static.prod-images.emergentagent.com/jobs/0e72f85f-e4b0-46dd-a92f-27b937d72463/images/ece9de530abfeb52ba1d5a3daea3272538a3150bc1336cb02f1243a7e7a66590.png"
              alt="Books" className="w-full h-auto rounded-md" />
          </div>
          <div className="absolute -bottom-6 -left-6 brutal-card bg-butter p-4 max-w-[230px] -rotate-3">
            <div className="text-xs uppercase tracking-[0.2em] font-bold">Last week's class avg</div>
            <div className="font-display font-black text-4xl mt-1">68%</div>
            <div className="text-xs mt-1 text-[#4A4A4A]">+14% vs the week before</div>
          </div>
        </div>
      </section>

      {/* Replaces section */}
      <section className="bg-white border-y-2 border-ink">
        <div className="max-w-7xl mx-auto px-6 py-16 text-center">
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-3">Built to replace</div>
          <h2 className="font-display font-extrabold text-3xl sm:text-4xl tracking-tight mb-3">No more juggling four logins.</h2>
          <p className="text-[#4A4A4A] max-w-2xl mx-auto">Maths drills + literacy + spaced revision + homework + lesson planning + comms — all in one. One annual price.</p>
          <div className="flex flex-wrap justify-center gap-3 mt-8">
            {["Maths drills", "Vocabulary", "Spaced revision", "Lesson planner", "Homework + AI marking", "Class chat"].map((t) => (
              <span key={t} className="px-3 py-1.5 border-2 border-ink rounded-full bg-mint text-sm font-bold">{t}</span>
            ))}
          </div>
        </div>
      </section>

      {/* For schools */}
      <section className="max-w-7xl mx-auto px-6 py-20 grid lg:grid-cols-3 gap-6">
        <div className="brutal-card p-8 bg-mint">
          <ChalkboardTeacher size={28} weight="duotone" />
          <h3 className="font-display font-bold text-2xl mt-4 mb-2">For teachers</h3>
          <p className="text-[#4A4A4A]">Plan a lesson in 30 seconds. Set homework, get class + per-student AI analysis with expected grades and next-lesson recommendations.</p>
        </div>
        <div className="brutal-card p-8 bg-lavender">
          <Trophy size={28} weight="duotone" />
          <h3 className="font-display font-bold text-2xl mt-4 mb-2">For students</h3>
          <p className="text-[#4A4A4A]">Practice, papers, AI tutor, Homework Helper, and a Dreams page that maps your career route step-by-step.</p>
        </div>
        <div className="brutal-card p-8 bg-peach">
          <ChartLineUp size={28} weight="duotone" />
          <h3 className="font-display font-bold text-2xl mt-4 mb-2">For SLT</h3>
          <p className="text-[#4A4A4A]">Detentions, attendance, achievement points logged once and visible to everyone who needs them. Whole-school annual price.</p>
        </div>
      </section>

      {/* Subjects */}
      <section className="bg-white border-y-2 border-ink">
        <div className="max-w-7xl mx-auto px-6 py-20">
          <div className="flex items-end justify-between mb-10 flex-wrap gap-4">
            <div>
              <div className="text-xs tracking-[0.2em] uppercase font-bold mb-3">23 subjects · 6 categories</div>
              <h2 className="font-display font-extrabold text-4xl sm:text-5xl tracking-tight">From phonics to PhD.</h2>
            </div>
            <p className="max-w-md text-[#4A4A4A]">UI shifts with age — voice-first for early years, gamified for primary, focused for secondary.</p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {SUBJECT_TILES.map((s) => (
              <div key={s.name} className="brutal-card p-6 flex flex-col items-start gap-4" style={{ backgroundColor: s.color }} data-testid={`subject-tile-${s.name.toLowerCase()}`}>
                <div className="border-2 border-ink bg-white rounded-md p-2 shadow-brutal"><s.icon size={26} weight="duotone" /></div>
                <div className="font-display font-bold text-xl">{s.name}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Homework helper teaser */}
      <section className="max-w-7xl mx-auto px-6 py-20 grid md:grid-cols-2 gap-10 items-center">
        <div>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-3">Stuck on homework?</div>
          <h2 className="font-display font-extrabold text-4xl sm:text-5xl tracking-tight mb-4">Paste it in. We'll teach, not give the answer.</h2>
          <p className="text-[#4A4A4A] text-lg mb-6 max-w-lg">Drop any question from any platform. Learnify asks what you don't understand — then walks you through that bit so you finish it yourself.</p>
          <Link to="/help" className="brutal-btn bg-ink text-white inline-flex items-center gap-2"><Question size={18} weight="bold" /> Try Homework Helper</Link>
        </div>
        <div className="brutal-card p-6 bg-butter">
          <div className="text-xs uppercase tracking-[0.2em] font-bold mb-3">Example session</div>
          <div className="space-y-3 text-sm">
            <div className="border-2 border-ink rounded-md p-3 bg-white"><strong>You:</strong> Solve 2(x − 3) = 14</div>
            <div className="border-2 border-ink rounded-md p-3 bg-mint"><strong>Learnify:</strong> Got it. Where are you stuck — distributing the 2, isolating x, or checking the answer?</div>
            <div className="border-2 border-ink rounded-md p-3 bg-white"><strong>You:</strong> Distributing</div>
            <div className="border-2 border-ink rounded-md p-3 bg-mint"><strong>Learnify:</strong> Multiply 2 by both terms in the bracket: 2·x = 2x, and 2·(−3) = −6. So 2(x − 3) = 2x − 6. Now try the next step...</div>
          </div>
        </div>
      </section>

      <footer className="border-t-2 border-ink py-10 text-center text-sm text-[#4A4A4A]">
        Built for serious learners. © {new Date().getFullYear()} Learnify.
      </footer>
    </div>
  );
}
