import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import AppLayout from "@/components/AppLayout";
import { findSubject, findTopic, GRADE_LEVELS } from "@/lib/subjects";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { ArrowLeft, Sparkle, Lightbulb, Cards, Question, ChatCircleDots, PaperPlaneTilt, ArrowRight, CheckCircle, XCircle, ArrowsClockwise } from "@phosphor-icons/react";
import { toast } from "sonner";

const TABS = [
  { id: "summary", label: "Summary", icon: Lightbulb },
  { id: "quiz", label: "Quiz", icon: Question },
  { id: "flashcards", label: "Flashcards", icon: Cards },
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
      const { data } = await api.post("/ai/generate", {
        subject: subject.name,
        topic: topic.name,
        sub_topic: subTopic || null,
        grade_level: user?.grade_level || "high_school",
        content_type: type,
      });
      setContent((prev) => ({ ...prev, [type]: data.content }));
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
                {GRADE_LEVELS.find((g) => g.value === user?.grade_level)?.label || "High School"}
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
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              data-testid={`tab-${t.id}`}
              className={`brutal-btn text-sm inline-flex items-center gap-2 ${activeTab === t.id ? "bg-ink text-white" : "bg-white hover:bg-butter"}`}
            >
              <t.icon size={16} weight="bold" /> {t.label}
            </button>
          ))}
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
          {activeTab === "tutor" && (
            <TutorView subject={subject.name} topic={topic.name} grade_level={user?.grade_level || "high_school"} />
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

function TutorView({ subject, topic, grade_level }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const send = async (e) => {
    e?.preventDefault();
    if (!input.trim() || loading) return;
    const text = input;
    setInput("");
    setMessages((m) => [...m, { role: "user", text }]);
    setLoading(true);
    try {
      const { data } = await api.post("/ai/chat", {
        subject, topic, grade_level, message: text, session_id: sessionId,
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
    <div className="flex flex-col h-[520px]" data-testid="tutor-content">
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-3 pb-3">
        {messages.length === 0 && (
          <div className="text-center text-[#4A4A4A] py-12">
            <ChatCircleDots size={32} weight="duotone" className="mx-auto mb-3" />
            <div className="font-display font-bold text-xl text-ink">Ask anything about {topic}.</div>
            <div className="text-sm mt-1">Examples: "Explain like I'm 12", "Give me a worked example", "Why does this matter?"</div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] border-2 border-ink rounded-md p-3 ${m.role === "user" ? "bg-ink text-white" : "bg-butter"}`}>
              <div className="text-xs uppercase tracking-[0.2em] font-bold mb-1 opacity-70">{m.role === "user" ? "You" : "Tutor"}</div>
              <div className="whitespace-pre-wrap text-sm leading-relaxed">{m.text}</div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex"><div className="border-2 border-ink rounded-md p-3 bg-butter text-sm font-mono">Thinking…</div></div>
        )}
      </div>
      <form onSubmit={send} className="flex gap-2 border-t-2 border-ink pt-3">
        <input
          data-testid="tutor-input"
          value={input} onChange={(e) => setInput(e.target.value)}
          placeholder="Ask your tutor…"
          className="brutal-input flex-1"
        />
        <button data-testid="tutor-send" type="submit" disabled={loading || !input.trim()}
          className="brutal-btn bg-ink text-white inline-flex items-center gap-2 disabled:opacity-60">
          <PaperPlaneTilt size={16} weight="bold" /> Send
        </button>
      </form>
    </div>
  );
}
