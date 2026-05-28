import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import AppLayout from "@/components/AppLayout";
import GradeLevelSelect from "@/components/GradeLevelSelect";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { SUBJECTS } from "@/lib/subjects";
import { Question, ClipboardText, PaperPlaneTilt, ArrowsClockwise, Sparkle, Warning } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Help() {
  const { user } = useAuth();
  const [problem, setProblem] = useState("");
  const [subject, setSubject] = useState("");
  const [gradeLevel, setGradeLevel] = useState(user?.grade_level || "high_school");
  const [messages, setMessages] = useState([]); // {role, text}
  const [sessionId, setSessionId] = useState(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (user?.grade_level) setGradeLevel(user.grade_level);
  }, [user?.grade_level]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const loadHistory = async () => {
    try {
      const { data } = await api.get("/ai/help/history");
      setHistory(data.items || []);
    } catch {}
  };
  useEffect(() => { loadHistory(); }, []);

  const startHelp = async (e) => {
    e?.preventDefault();
    if (!problem.trim()) { toast.error("Paste a problem first."); return; }
    setMessages([{ role: "user", text: problem }]);
    setLoading(true);
    try {
      const { data } = await api.post("/ai/help", {
        problem,
        grade_level: gradeLevel,
        subject: subject || null,
      });
      setSessionId(data.session_id);
      setMessages((m) => [...m, { role: "assistant", text: data.response }]);
      loadHistory();
    } catch (ex) {
      const status = ex.response?.status;
      const msg = ex.response?.data?.detail || "Something went wrong";
      if (status === 402) {
        toast.error(msg, { action: { label: "Upgrade", onClick: () => { window.location.href = "/pricing"; } } });
      } else {
        toast.error(msg);
      }
      setMessages((m) => m.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  const sendFollowUp = async (e) => {
    e?.preventDefault();
    if (!input.trim() || loading) return;
    const text = input;
    setInput("");
    setMessages((m) => [...m, { role: "user", text }]);
    setLoading(true);
    try {
      const { data } = await api.post("/ai/help", {
        problem,
        message: text,
        grade_level: gradeLevel,
        subject: subject || null,
        session_id: sessionId,
      });
      setMessages((m) => [...m, { role: "assistant", text: data.response }]);
    } catch (ex) {
      const status = ex.response?.status;
      const msg = ex.response?.data?.detail || "Something went wrong";
      if (status === 402) {
        toast.error(msg, { action: { label: "Upgrade", onClick: () => { window.location.href = "/pricing"; } } });
      } else {
        toast.error(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setProblem("");
    setMessages([]);
    setSessionId(null);
    setInput("");
  };

  const inSession = messages.length > 0;

  return (
    <AppLayout>
      <div className="max-w-5xl space-y-6">
        <div>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A]">Homework Helper</div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Stuck? Paste it here.</h1>
          <p className="text-[#4A4A4A] mt-3 max-w-2xl">
            Drop any homework question — from Sparx Maths, MyMaths, Seneca, a textbook, worksheet, whatever. ScholarHub won't just give you the answer. It asks what you don't understand, then teaches you that bit. You finish the problem yourself.
          </p>
        </div>

        {!inSession && (
          <form onSubmit={startHelp} className="brutal-card p-6 space-y-4">
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold flex items-center gap-2">
                <ClipboardText size={14} /> Paste your homework problem
              </span>
              <textarea
                data-testid="help-problem-input"
                value={problem} onChange={(e) => setProblem(e.target.value)}
                required minLength={3} rows={5}
                placeholder="e.g., Expand and simplify (2x − 3)(x + 4)"
                className="mt-2 brutal-input w-full font-mono text-sm"
              />
            </label>
            <div className="grid sm:grid-cols-2 gap-3">
              <label className="block">
                <span className="text-xs uppercase tracking-[0.2em] font-bold">Subject (optional)</span>
                <select
                  data-testid="help-subject-select"
                  value={subject} onChange={(e) => setSubject(e.target.value)}
                  className="mt-2 brutal-input w-full bg-white"
                >
                  <option value="">Auto-detect</option>
                  {SUBJECTS.map((s) => <option key={s.id} value={s.name}>{s.name}</option>)}
                </select>
              </label>
              <label className="block">
                <span className="text-xs uppercase tracking-[0.2em] font-bold">Your level</span>
                <GradeLevelSelect
                  testId="help-grade-select"
                  value={gradeLevel}
                  onChange={(v) => setGradeLevel(v)}
                  className="mt-2 w-full"
                />
              </label>
            </div>
            <button
              type="submit" disabled={loading}
              data-testid="help-submit-btn"
              className="brutal-btn bg-ink text-white w-full inline-flex items-center justify-center gap-2 disabled:opacity-60"
            >
              <Sparkle size={18} weight="bold" /> {loading ? "Thinking…" : "Help me with this"}
            </button>
            <p className="text-xs text-[#4A4A4A]">
              <Warning size={12} className="inline mb-0.5" /> Tip: paste the FULL question so it has all the numbers/wording.
            </p>
          </form>
        )}

        {inSession && (
          <div className="brutal-card p-5 bg-butter" data-testid="help-problem-display">
            <div className="text-xs uppercase tracking-[0.2em] font-bold mb-2">Your problem</div>
            <div className="font-mono text-sm whitespace-pre-wrap">{problem}</div>
            <button onClick={reset} className="mt-3 brutal-btn bg-white inline-flex items-center gap-2 text-sm" data-testid="help-reset-btn">
              <ArrowsClockwise size={14} weight="bold" /> Different problem
            </button>
          </div>
        )}

        {inSession && (
          <div className="brutal-card p-5 bg-white">
            <div ref={scrollRef} className="space-y-3 max-h-[560px] overflow-y-auto pr-2" data-testid="help-chat-thread">
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[88%] border-2 border-ink rounded-md p-3 ${m.role === "user" ? "bg-ink text-white" : "bg-butter"}`}>
                    <div className="text-xs uppercase tracking-[0.2em] font-bold mb-1 opacity-70">
                      {m.role === "user" ? "You" : "Helper"}
                    </div>
                    <div className="whitespace-pre-wrap text-sm leading-relaxed">{m.text}</div>
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex"><div className="border-2 border-ink rounded-md p-3 bg-butter text-sm font-mono">Thinking…</div></div>
              )}
            </div>

            <form onSubmit={sendFollowUp} className="flex gap-2 border-t-2 border-ink pt-3 mt-3">
              <input
                data-testid="help-followup-input"
                value={input} onChange={(e) => setInput(e.target.value)}
                placeholder="Reply — say what part you don't get…"
                className="brutal-input flex-1"
                disabled={loading}
              />
              <button data-testid="help-followup-send" type="submit" disabled={loading || !input.trim()}
                className="brutal-btn bg-ink text-white inline-flex items-center gap-2 disabled:opacity-60">
                <PaperPlaneTilt size={16} weight="bold" /> Send
              </button>
            </form>
          </div>
        )}

        {!inSession && history.length > 0 && (
          <section data-testid="help-history">
            <div className="text-xs uppercase tracking-[0.2em] font-bold mb-3">Recent problems</div>
            <div className="space-y-2">
              {history.slice(0, 5).map((h) => (
                <button
                  key={h.session_id}
                  onClick={() => { setProblem(h.problem || ""); }}
                  className="brutal-card p-3 w-full text-left flex items-center gap-3 bg-white"
                  data-testid={`help-history-${h.session_id}`}
                >
                  <Question size={18} weight="duotone" className="shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm truncate">{h.problem}</div>
                    <div className="text-xs text-[#4A4A4A]">{new Date(h.created_at).toLocaleString()}</div>
                  </div>
                </button>
              ))}
            </div>
          </section>
        )}

        {!inSession && (
          <div className="brutal-card p-5 bg-lavender text-sm">
            <strong>How this works:</strong> ScholarHub uses Socratic teaching. It restates the problem, asks what's confusing you, then teaches just that piece. You always finish the question yourself — that's how the learning sticks. {" "}
            <Link to="/pricing" className="font-bold underline underline-offset-4">Upgrade your plan</Link> for unlimited daily use.
          </div>
        )}
      </div>
    </AppLayout>
  );
}
