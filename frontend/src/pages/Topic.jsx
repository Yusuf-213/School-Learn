import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import AppLayout from "@/components/AppLayout";
import { findSubject, findTopic, gradeLevelLabel, EXAM_BOARDS } from "@/lib/subjects";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { ArrowLeft, Sparkle, Lightbulb, Cards, Question, ChatCircleDots, PaperPlaneTilt, ArrowRight, CheckCircle, XCircle, ArrowsClockwise, FileText, Printer, Prohibit, Image as ImageIcon, X, Clock } from "@phosphor-icons/react";
import { toast } from "sonner";

const TABS = [
  { id: "summary", label: "Summary", icon: Lightbulb },
  { id: "quiz", label: "Quiz", icon: Question },
  { id: "flashcards", label: "Flashcards", icon: Cards },
  { id: "paper", label: "Practice Paper", icon: FileText },
  { id: "tutor", label: "AI Tutor", icon: ChatCircleDots },
];

export default function Topic() {
  const { subjectId, topicId } = useParams();
  const { user } = useAuth();
  const subject = findSubject(subjectId);
  const topic = findTopic(subjectId, topicId);
  const [activeTab, setActiveTab] = useState("summary");
  const [subTopic, setSubTopic] = useState("");
  const [content, setContent] = useState({});
  const [loading, setLoading] = useState(false);
  const [examBoard, setExamBoard] = useState("generic");
  const [allowTutor, setAllowTutor] = useState(true);         // toggle when generating assessments
  const [assessmentLockTutor, setAssessmentLockTutor] = useState(false); // true if the last generated paper/quiz forbids tutor
  const [lockedUntil, setLockedUntil] = useState("");         // datetime-local string chosen by teacher/student in the form
  const [activeLockUntilIso, setActiveLockUntilIso] = useState(null); // ISO string returned by backend when tutor is currently locked
  const [now, setNow] = useState(Date.now());

  // Ticker so the countdown updates every second and auto-unlocks
  useEffect(() => {
    if (!assessmentLockTutor || !activeLockUntilIso) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [assessmentLockTutor, activeLockUntilIso]);

  useEffect(() => {
    if (!assessmentLockTutor || !activeLockUntilIso) return;
    if (new Date(activeLockUntilIso).getTime() <= now) {
      setAssessmentLockTutor(false);
      setActiveLockUntilIso(null);
      toast.success("AI tutor is now unlocked for this assessment.");
    }
  }, [now, assessmentLockTutor, activeLockUntilIso]);

  if (!subject || !topic) {
    return (
      <AppLayout>
        <div className="max-w-3xl">
          <Link to="/subjects" className="text-sm font-bold underline">← Subjects</Link>
          <h1 className="font-display font-black text-3xl mt-4">Topic not found.</h1>
        </div>
      </AppLayout>
    );
  }

  const generate = async (type) => {
    setLoading(true);
    try {
      const payload = {
        subject: subject.name,
        topic: topic.name,
        sub_topic: subTopic || null,
        grade_level: user?.grade_level || "high_school",
        content_type: type,
      };
      if (type === "paper" || type === "quiz") {
        payload.exam_board = examBoard;
        payload.allow_tutor = allowTutor;
        if (!allowTutor && lockedUntil) {
          // datetime-local value is local time — convert to ISO (UTC) so backend stores it safely
          payload.tutor_locked_until = new Date(lockedUntil).toISOString();
        }
      }
      const { data } = await api.post("/ai/generate", payload);
      setContent((prev) => ({ ...prev, [type]: data.content }));
      if (type === "paper" || type === "quiz") {
        const locked = data.allow_tutor === false;
        setAssessmentLockTutor(locked);
        setActiveLockUntilIso(locked ? (data.tutor_locked_until || null) : null);
        setNow(Date.now());
        if (locked && activeTab === "tutor") setActiveTab(type);
      }
      // Track progress
      api.post("/progress", { subject: subjectId, topic: topicId, completed: false }).catch(() => {});
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to generate content");
    } finally {
      setLoading(false);
    }
  };

  const markComplete = async () => {
    try {
      await api.post("/progress", { subject: subjectId, topic: topicId, completed: true });
      toast.success("Marked complete. Nice work.");
    } catch {}
  };

  return (
    <AppLayout>
      <div className="max-w-5xl space-y-6">
        <Link to={`/subjects/${subjectId}`} className="inline-flex items-center gap-2 text-sm font-bold" data-testid="back-to-subject">
          <ArrowLeft size={16} weight="bold" /> {subject.name}
        </Link>

        <div className="brutal-card p-8" style={{ backgroundColor: subject.accentHex }}>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2">{subject.name}</div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight mb-4">{topic.name}</h1>

          <div className="flex flex-wrap items-end gap-3 mt-4">
            <label className="block grow min-w-[220px]">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Focus on (optional)</span>
              <select
                data-testid="topic-subtopic-select"
                value={subTopic} onChange={(e) => setSubTopic(e.target.value)}
                className="mt-2 brutal-input w-full bg-white"
              >
                <option value="">Whole topic</option>
                {topic.sub.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </label>
            <div className="text-sm">
              <div className="text-xs uppercase tracking-[0.2em] font-bold mb-2">Level</div>
              <div className="brutal-input bg-white py-2 px-3 text-sm">
                {gradeLevelLabel(user?.grade_level) || "High School"}
              </div>
            </div>
            <button
              onClick={markComplete}
              data-testid="mark-complete-btn"
              className="brutal-btn bg-ink text-white inline-flex items-center gap-2 text-sm"
            >
              <CheckCircle size={16} weight="bold" /> Mark complete
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex flex-wrap gap-2">
          {TABS.map((t) => {
            const tutorLocked = t.id === "tutor" && assessmentLockTutor;
            const timerSuffix = tutorLocked && activeLockUntilIso ? ` · ${formatCountdown(activeLockUntilIso, now)}` : (tutorLocked ? " · locked" : "");
            return (
              <button
                key={t.id}
                onClick={() => { if (!tutorLocked) setActiveTab(t.id); }}
                disabled={tutorLocked}
                title={tutorLocked ? (activeLockUntilIso ? `AI tutor unlocks at ${new Date(activeLockUntilIso).toLocaleString()}` : "AI tutor is disabled for the active assessment") : undefined}
                data-testid={`tab-${t.id}`}
                className={`brutal-btn text-sm inline-flex items-center gap-2 ${activeTab === t.id ? "bg-ink text-white" : "bg-white hover:bg-butter"} ${tutorLocked ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                <t.icon size={16} weight="bold" /> {t.label}{timerSuffix}
              </button>
            );
          })}
        </div>

        {/* Tab body */}
        <div className="brutal-card p-6 bg-white min-h-[300px]">
          {activeTab === "summary" && (
            <SummaryView data={content.summary} loading={loading} onGenerate={() => generate("summary")} />
          )}
          {activeTab === "quiz" && (
            <QuizView data={content.quiz} loading={loading} onGenerate={() => generate("quiz")} />
          )}
          {activeTab === "flashcards" && (
            <FlashcardsView data={content.flashcards} loading={loading} onGenerate={() => generate("flashcards")} />
          )}
          {activeTab === "paper" && (
            <PaperView
              data={content.paper}
              loading={loading}
              onGenerate={() => generate("paper")}
              examBoard={examBoard}
              setExamBoard={setExamBoard}
              allowTutor={allowTutor}
              setAllowTutor={setAllowTutor}
              lockedUntil={lockedUntil}
              setLockedUntil={setLockedUntil}
              assessmentLockTutor={assessmentLockTutor}
              activeLockUntilIso={activeLockUntilIso}
              now={now}
            />
          )}
          {activeTab === "tutor" && (
            assessmentLockTutor
              ? <TutorLockedNotice activeLockUntilIso={activeLockUntilIso} now={now} />
              : <TutorView subject={subject.name} topic={topic.name} grade_level={user?.grade_level || "high_school"} />
          )}
        </div>
      </div>
    </AppLayout>
  );
}

function GenerateEmpty({ onGenerate, label, loading }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-10">
      <Sparkle size={36} weight="duotone" />
      <div className="font-display font-bold text-2xl mt-4">Generate {label}</div>
      <div className="text-[#4A4A4A] text-sm mt-2 max-w-md">Tap below to have your AI tutor create this for you at your grade level.</div>
      <button
        onClick={onGenerate} disabled={loading}
        data-testid={`generate-${label.toLowerCase()}-btn`}
        className="mt-6 brutal-btn bg-ink text-white inline-flex items-center gap-2 disabled:opacity-60"
      >
        <Sparkle size={16} weight="bold" /> {loading ? "Generating…" : `Generate ${label}`}
      </button>
    </div>
  );
}

function SummaryView({ data, onGenerate, loading }) {
  if (!data) return <GenerateEmpty label="Summary" onGenerate={onGenerate} loading={loading} />;
  return (
    <div className="space-y-5" data-testid="summary-content">
      <h2 className="font-display font-extrabold text-2xl tracking-tight">{data.title}</h2>
      <div>
        <div className="text-xs uppercase tracking-[0.2em] font-bold mb-2">Key points</div>
        <ul className="space-y-2">
          {data.key_points?.map((kp, i) => (
            <li key={i} className="flex gap-3"><span className="font-bold">{i + 1}.</span><span>{kp}</span></li>
          ))}
        </ul>
      </div>
      {data.definitions?.length > 0 && (
        <div>
          <div className="text-xs uppercase tracking-[0.2em] font-bold mb-2">Definitions</div>
          <div className="grid sm:grid-cols-2 gap-3">
            {data.definitions.map((d, i) => (
              <div key={i} className="border-2 border-ink rounded-md p-3 bg-butter">
                <div className="font-bold">{d.term}</div>
                <div className="text-sm text-[#4A4A4A]">{d.meaning}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      {data.example && (
        <div className="border-2 border-ink rounded-md p-4 bg-mint">
          <div className="text-xs uppercase tracking-[0.2em] font-bold mb-2">Example</div>
          <p>{data.example}</p>
        </div>
      )}
      {data.memory_tip && (
        <div className="border-2 border-ink rounded-md p-4 bg-lavender">
          <div className="text-xs uppercase tracking-[0.2em] font-bold mb-2">Memory tip</div>
          <p>{data.memory_tip}</p>
        </div>
      )}
      <button onClick={onGenerate} disabled={loading} className="brutal-btn bg-white inline-flex items-center gap-2 text-sm">
        <ArrowsClockwise size={16} weight="bold" /> Regenerate
      </button>
    </div>
  );
}

function QuizView({ data, onGenerate, loading }) {
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => { setAnswers({}); setSubmitted(false); }, [data]);
  if (!data) return <GenerateEmpty label="Quiz" onGenerate={onGenerate} loading={loading} />;

  const score = data.questions?.reduce(
    (acc, q, i) => acc + (answers[i] === q.correct_index ? 1 : 0), 0
  );

  return (
    <div className="space-y-5" data-testid="quiz-content">
      {data.questions?.map((q, qi) => (
        <div key={qi} className="border-2 border-ink rounded-md p-4 bg-white">
          <div className="font-bold mb-3">{qi + 1}. {q.question}</div>
          <div className="grid gap-2">
            {q.options.map((opt, oi) => {
              const picked = answers[qi] === oi;
              const correct = submitted && q.correct_index === oi;
              const wrong = submitted && picked && q.correct_index !== oi;
              return (
                <button
                  key={oi}
                  disabled={submitted}
                  onClick={() => setAnswers({ ...answers, [qi]: oi })}
                  data-testid={`quiz-q${qi}-opt${oi}`}
                  className={`text-left border-2 rounded-md p-3 transition-all ${
                    correct ? "border-ink bg-mint" :
                    wrong ? "border-focus bg-peach" :
                    picked ? "border-ink bg-butter shadow-brutal" :
                    "border-ink bg-white hover:bg-butter"
                  }`}
                >
                  <span className="font-bold mr-2">{String.fromCharCode(65 + oi)}.</span>{opt}
                </button>
              );
            })}
          </div>
          {submitted && (
            <div className="mt-3 text-sm flex items-start gap-2">
              {answers[qi] === q.correct_index
                ? <CheckCircle size={18} weight="fill" className="shrink-0 mt-0.5" />
                : <XCircle size={18} weight="fill" className="shrink-0 mt-0.5 text-focus" />}
              <span>{q.explanation}</span>
            </div>
          )}
        </div>
      ))}

      {!submitted ? (
        <button
          onClick={() => setSubmitted(true)}
          disabled={Object.keys(answers).length < (data.questions?.length || 0)}
          data-testid="quiz-submit-btn"
          className="brutal-btn bg-ink text-white disabled:opacity-50"
        >
          Submit answers
        </button>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <div className="brutal-card px-4 py-2 bg-butter">
            <span className="font-display font-black text-2xl">{score}/{data.questions.length}</span>
            <span className="text-sm ml-2">correct</span>
          </div>
          <button onClick={onGenerate} disabled={loading} className="brutal-btn bg-white inline-flex items-center gap-2">
            <ArrowsClockwise size={16} weight="bold" /> New quiz
          </button>
        </div>
      )}
    </div>
  );
}

function FlashcardsView({ data, onGenerate, loading }) {
  const [idx, setIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);

  useEffect(() => { setIdx(0); setFlipped(false); }, [data]);
  if (!data) return <GenerateEmpty label="Flashcards" onGenerate={onGenerate} loading={loading} />;

  const card = data.cards?.[idx];
  if (!card) return null;

  return (
    <div className="space-y-4" data-testid="flashcards-content">
      <div className="text-xs uppercase tracking-[0.2em] font-bold">Card {idx + 1} / {data.cards.length}</div>
      <button
        onClick={() => setFlipped(!flipped)}
        data-testid="flashcard-flip"
        className="w-full text-left border-2 border-ink rounded-lg shadow-brutal-lg bg-butter p-10 min-h-[220px] flex items-center justify-center hover:-translate-y-0.5 transition-all"
      >
        <div className="text-center">
          <div className="text-xs uppercase tracking-[0.2em] font-bold mb-3">{flipped ? "Back" : "Front"}</div>
          <div className="font-display font-bold text-2xl">{flipped ? card.back : card.front}</div>
          {!flipped && <div className="text-xs text-[#4A4A4A] mt-4">Tap to reveal answer</div>}
        </div>
      </button>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2">
          <button
            data-testid="flashcard-prev"
            onClick={() => { setIdx((i) => Math.max(0, i - 1)); setFlipped(false); }}
            disabled={idx === 0}
            className="brutal-btn bg-white inline-flex items-center gap-2 disabled:opacity-50">
            <ArrowLeft size={16} weight="bold" /> Prev
          </button>
          <button
            data-testid="flashcard-next"
            onClick={() => { setIdx((i) => Math.min(data.cards.length - 1, i + 1)); setFlipped(false); }}
            disabled={idx >= data.cards.length - 1}
            className="brutal-btn bg-white inline-flex items-center gap-2 disabled:opacity-50">
            Next <ArrowRight size={16} weight="bold" />
          </button>
        </div>
        <button onClick={onGenerate} disabled={loading} className="brutal-btn bg-white inline-flex items-center gap-2 text-sm">
          <ArrowsClockwise size={16} weight="bold" /> New deck
        </button>
      </div>
    </div>
  );
}

function formatCountdown(iso, nowMs) {
  if (!iso) return "";
  const diff = new Date(iso).getTime() - (nowMs || Date.now());
  if (diff <= 0) return "unlocked";
  const s = Math.floor(diff / 1000);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `unlocks in ${h}h ${m}m`;
  if (m > 0) return `unlocks in ${m}m ${sec}s`;
  return `unlocks in ${sec}s`;
}

function PaperView({ data, onGenerate, loading, examBoard, setExamBoard, allowTutor, setAllowTutor, lockedUntil, setLockedUntil, assessmentLockTutor, activeLockUntilIso, now }) {
  return (
    <div className="space-y-4" data-testid="paper-content">
      <div className="flex flex-wrap items-end gap-3 border-b-2 border-ink pb-4">
        <label className="block">
          <span className="text-xs uppercase tracking-[0.2em] font-bold">Exam board</span>
          <select
            data-testid="paper-board-select"
            value={examBoard} onChange={(e) => setExamBoard(e.target.value)}
            className="mt-2 brutal-input bg-white py-2 px-3 text-sm"
          >
            {EXAM_BOARDS.map((b) => <option key={b.value} value={b.value}>{b.label}</option>)}
          </select>
        </label>
        <label className="inline-flex items-center gap-2 border-2 border-ink rounded-md bg-white px-3 py-2 text-sm cursor-pointer" data-testid="paper-allow-tutor-toggle">
          <input
            type="checkbox"
            checked={!!allowTutor}
            onChange={(e) => setAllowTutor(e.target.checked)}
            className="h-4 w-4 accent-black"
            data-testid="paper-allow-tutor-checkbox"
          />
          <span className="font-bold">Allow AI tutor</span>
          <span className="text-xs text-[#4A4A4A]">during this assessment</span>
        </label>
        {!allowTutor && (
          <label className="block" data-testid="paper-lock-until-wrap">
            <span className="text-xs uppercase tracking-[0.2em] font-bold flex items-center gap-1">
              <Clock size={12} weight="bold" /> Auto-unlock at (optional)
            </span>
            <input
              type="datetime-local"
              value={lockedUntil || ""}
              onChange={(e) => setLockedUntil(e.target.value)}
              className="mt-2 brutal-input bg-white py-2 px-3 text-sm"
              data-testid="paper-lock-until-input"
              min={new Date(Date.now() + 60000).toISOString().slice(0, 16)}
            />
          </label>
        )}
        <button
          onClick={onGenerate} disabled={loading}
          data-testid="paper-generate-btn"
          className="brutal-btn bg-ink text-white inline-flex items-center gap-2 disabled:opacity-60"
        >
          <Sparkle size={16} weight="bold" /> {loading ? "Generating…" : data ? "Regenerate paper" : "Generate paper"}
        </button>
        {data && (
          <button onClick={() => window.print()} className="brutal-btn bg-white inline-flex items-center gap-2 text-sm" data-testid="paper-print-btn">
            <Printer size={16} weight="bold" /> Print / PDF
          </button>
        )}
      </div>

      {data && assessmentLockTutor && (
        <div className="brutal-card p-3 bg-peach text-sm inline-flex items-center gap-2" data-testid="paper-tutor-locked-banner">
          <Prohibit size={16} weight="bold" />
          AI tutor is <strong>locked</strong> for this assessment
          {activeLockUntilIso ? (
            <>
              — {formatCountdown(activeLockUntilIso, now)} (at {new Date(activeLockUntilIso).toLocaleString()}).
            </>
          ) : (
            <> — regenerate with "Allow AI tutor" ticked to enable it.</>
          )}
        </div>
      )}

      {!data ? (
        <div className="text-center py-10">
          <FileText size={36} weight="duotone" className="mx-auto" />
          <div className="font-display font-bold text-xl mt-3">Generate a full practice paper.</div>
          <p className="text-[#4A4A4A] text-sm mt-2 max-w-md mx-auto">
            Structured questions in real exam style with a mark scheme at the end. Papers require a Basic plan or higher; exam-board mapped papers require Pro.
          </p>
        </div>
      ) : (
        <div className="print:bg-white" id="paper-printable">
          <div className="border-b-2 border-ink pb-4 mb-6">
            <h2 className="font-display font-extrabold text-2xl tracking-tight">{data.title}</h2>
            <div className="flex flex-wrap gap-4 mt-2 text-sm text-[#4A4A4A]">
              {data.duration_minutes > 0 && <span><strong>Duration:</strong> {data.duration_minutes} min</span>}
              {data.total_marks > 0 && <span><strong>Total marks:</strong> {data.total_marks}</span>}
            </div>
            {data.instructions && <p className="mt-3 italic">{data.instructions}</p>}
          </div>

          {data.sections?.map((sec, si) => (
            <div key={si} className="mb-6">
              <div className="text-xs uppercase tracking-[0.2em] font-bold mb-3">{sec.name}</div>
              <div className="space-y-5">
                {sec.questions?.map((q, qi) => (
                  <div key={qi} className="border-2 border-ink rounded-md p-4 bg-white">
                    <div className="flex justify-between gap-3 mb-2">
                      <div className="font-bold">Q{q.number}. {q.question}</div>
                      {q.marks > 0 && <span className="text-sm font-bold whitespace-nowrap">[{q.marks} marks]</span>}
                    </div>
                    {q.parts?.length > 0 && (
                      <ol className="mt-3 space-y-2 pl-1">
                        {q.parts.map((p, pi) => (
                          <li key={pi} className="flex justify-between gap-3">
                            <span><strong>({p.label})</strong> {p.question}</span>
                            {p.marks > 0 && <span className="text-sm font-bold whitespace-nowrap">[{p.marks}]</span>}
                          </li>
                        ))}
                      </ol>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}

          {data.mark_scheme?.length > 0 && (
            <details className="brutal-card p-5 bg-butter mt-6" data-testid="paper-markscheme">
              <summary className="font-display font-bold text-lg cursor-pointer">Mark scheme</summary>
              <ol className="mt-3 space-y-3 text-sm">
                {data.mark_scheme.map((m, i) => (
                  <li key={i}><strong>{m.q}:</strong> {m.answer}</li>
                ))}
              </ol>
            </details>
          )}
        </div>
      )}
    </div>
  );
}

function TutorLockedNotice({ activeLockUntilIso, now }) {
  const untilLabel = activeLockUntilIso ? new Date(activeLockUntilIso).toLocaleString() : null;
  const countdown = activeLockUntilIso ? formatCountdown(activeLockUntilIso, now) : null;
  return (
    <div className="flex flex-col items-center justify-center text-center py-12" data-testid="tutor-locked">
      <Prohibit size={40} weight="duotone" />
      <div className="font-display font-bold text-2xl mt-4">AI Tutor is locked</div>
      <p className="text-[#4A4A4A] text-sm mt-2 max-w-md">
        Your current assessment on this topic was generated with the AI tutor <strong>disabled</strong>.
        {untilLabel
          ? <> It will <strong>auto-unlock</strong> at {untilLabel}.</>
          : <> Regenerate the paper with "Allow AI tutor" turned on to unlock it.</>}
      </p>
      {countdown && (
        <div className="mt-4 brutal-card px-4 py-2 bg-butter inline-flex items-center gap-2" data-testid="tutor-lock-countdown">
          <Clock size={16} weight="bold" />
          <span className="font-mono font-bold">{countdown}</span>
        </div>
      )}
    </div>
  );
}

function TutorView({ subject, topic, grade_level }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [images, setImages] = useState([]);
  const scrollRef = useRef(null);
  const fileRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const fileToDataUrl = (file) => new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = reject;
    r.readAsDataURL(file);
  });

  const onPaste = async (e) => {
    const out = [];
    for (const it of (e.clipboardData?.items || [])) {
      if (it.type && it.type.startsWith("image/")) {
        const f = it.getAsFile();
        if (f) out.push(await fileToDataUrl(f));
        if (out.length >= 4) break;
      }
    }
    if (out.length) {
      e.preventDefault();
      setImages((cur) => [...cur, ...out].slice(0, 4));
      toast.success(`${out.length} image${out.length > 1 ? "s" : ""} attached`);
    }
  };

  const pickFiles = async (files) => {
    const arr = Array.from(files || []).filter((f) => f.type.startsWith("image/"));
    const urls = await Promise.all(arr.map(fileToDataUrl));
    setImages((cur) => [...cur, ...urls].slice(0, 4));
  };

  const send = async (e) => {
    e?.preventDefault();
    const hasText = input.trim().length > 0;
    const hasImgs = images.length > 0;
    if ((!hasText && !hasImgs) || loading) return;
    const text = input || "(image attached)";
    const imgsForTurn = images;
    setInput("");
    setImages([]);
    setMessages((m) => [...m, { role: "user", text, images: imgsForTurn }]);
    setLoading(true);
    try {
      const { data } = await api.post("/ai/chat", {
        subject, topic, grade_level, message: text, session_id: sessionId,
        images: imgsForTurn.length ? imgsForTurn : null,
      });
      setSessionId(data.session_id);
      setMessages((m) => [...m, { role: "assistant", text: data.response }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: "Sorry, I had trouble answering. Try again?" }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[560px]" data-testid="tutor-content">
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-3 pb-3">
        {messages.length === 0 && (
          <div className="text-center text-[#4A4A4A] py-12">
            <ChatCircleDots size={32} weight="duotone" className="mx-auto mb-3" />
            <div className="font-display font-bold text-xl text-ink">Ask anything about {topic}.</div>
            <div className="text-sm mt-1">Type a question or paste a screenshot (Ctrl/Cmd + V).</div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] border-2 border-ink rounded-md p-3 ${m.role === "user" ? "bg-ink text-white" : "bg-butter"}`}>
              <div className="text-xs uppercase tracking-[0.2em] font-bold mb-1 opacity-70">{m.role === "user" ? "You" : "Tutor"}</div>
              {m.images?.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2">
                  {m.images.map((src, k) => (
                    <img key={k} src={src} alt={`tutor-img-${k}`} className="h-20 w-20 object-cover border-2 border-white/40 rounded-md" />
                  ))}
                </div>
              )}
              <div className="whitespace-pre-wrap text-sm leading-relaxed">{m.text}</div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex"><div className="border-2 border-ink rounded-md p-3 bg-butter text-sm font-mono">Thinking…</div></div>
        )}
      </div>

      {images.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2" data-testid="tutor-image-chips">
          {images.map((src, i) => (
            <div key={i} className="relative">
              <img src={src} alt={`attach-${i}`} className="h-14 w-14 object-cover border-2 border-ink rounded-md" data-testid={`tutor-image-${i}`} />
              <button
                type="button"
                onClick={() => setImages((cur) => cur.filter((_, k) => k !== i))}
                className="absolute -top-2 -right-2 bg-ink text-white rounded-full border-2 border-white p-0.5 hover:bg-focus"
                data-testid={`tutor-image-remove-${i}`}
                aria-label="Remove image"
              >
                <X size={12} weight="bold" />
              </button>
            </div>
          ))}
        </div>
      )}

      <form onSubmit={send} className="flex gap-2 border-t-2 border-ink pt-3">
        <input
          data-testid="tutor-input"
          value={input} onChange={(e) => setInput(e.target.value)}
          onPaste={onPaste}
          placeholder="Ask your tutor — or paste a screenshot…"
          className="brutal-input flex-1"
        />
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(e) => { pickFiles(e.target.files); e.target.value = ""; }}
          data-testid="tutor-file-input"
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="brutal-btn bg-white hover:bg-butter"
          title="Attach image"
          data-testid="tutor-attach-btn"
        >
          <ImageIcon size={16} weight="bold" />
        </button>
        <button data-testid="tutor-send" type="submit" disabled={loading || (!input.trim() && images.length === 0)}
          className="brutal-btn bg-ink text-white inline-flex items-center gap-2 disabled:opacity-60">
          <PaperPlaneTilt size={16} weight="bold" /> Send
        </button>
      </form>
    </div>
  );
}
