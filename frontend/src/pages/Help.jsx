import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import AppLayout from "@/components/AppLayout";
import GradeLevelSelect from "@/components/GradeLevelSelect";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { SUBJECTS } from "@/lib/subjects";
import { Question, ClipboardText, PaperPlaneTilt, ArrowsClockwise, Sparkle, Warning, Image as ImageIcon, X } from "@phosphor-icons/react";
import { toast } from "sonner";

// Read a File/Blob into a data URL (base64)
function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = reject;
    r.readAsDataURL(file);
  });
}

async function collectImagesFromClipboard(e, cap = 4) {
  const out = [];
  const items = e.clipboardData?.items || [];
  for (const it of items) {
    if (it.type && it.type.startsWith("image/")) {
      const f = it.getAsFile();
      if (f) out.push(await fileToDataUrl(f));
      if (out.length >= cap) break;
    }
  }
  return out;
}

export default function Help() {
  const { user } = useAuth();
  const [problem, setProblem] = useState("");
  const [subject, setSubject] = useState("");
  const [gradeLevel, setGradeLevel] = useState(user?.grade_level || "high_school");
  const [messages, setMessages] = useState([]); // {role, text, images?}
  const [sessionId, setSessionId] = useState(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [problemImages, setProblemImages] = useState([]);   // images attached to the FIRST turn
  const [followImages, setFollowImages] = useState([]);     // images attached to a FOLLOW-UP turn
  const scrollRef = useRef(null);
  const problemFileRef = useRef(null);
  const followFileRef = useRef(null);

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

  const onPasteProblem = async (e) => {
    const imgs = await collectImagesFromClipboard(e);
    if (imgs.length) {
      e.preventDefault();
      setProblemImages((cur) => [...cur, ...imgs].slice(0, 4));
      toast.success(`${imgs.length} image${imgs.length > 1 ? "s" : ""} attached`);
    }
  };
  const onPasteFollow = async (e) => {
    const imgs = await collectImagesFromClipboard(e);
    if (imgs.length) {
      e.preventDefault();
      setFollowImages((cur) => [...cur, ...imgs].slice(0, 4));
      toast.success(`${imgs.length} image${imgs.length > 1 ? "s" : ""} attached`);
    }
  };

  const pickProblemFiles = async (files) => {
    const arr = Array.from(files || []).filter((f) => f.type.startsWith("image/"));
    const urls = await Promise.all(arr.map(fileToDataUrl));
    setProblemImages((cur) => [...cur, ...urls].slice(0, 4));
  };
  const pickFollowFiles = async (files) => {
    const arr = Array.from(files || []).filter((f) => f.type.startsWith("image/"));
    const urls = await Promise.all(arr.map(fileToDataUrl));
    setFollowImages((cur) => [...cur, ...urls].slice(0, 4));
  };

  const startHelp = async (e) => {
    e?.preventDefault();
    const hasText = problem.trim().length > 0;
    const hasImgs = problemImages.length > 0;
    if (!hasText && !hasImgs) { toast.error("Paste a problem or an image first."); return; }
    setMessages([{ role: "user", text: problem || "(image attached)", images: problemImages }]);
    setLoading(true);
    try {
      const { data } = await api.post("/ai/help", {
        problem: problem || "See attached image(s).",
        grade_level: gradeLevel,
        subject: subject || null,
        images: problemImages.length ? problemImages : null,
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
    const hasText = input.trim().length > 0;
    const hasImgs = followImages.length > 0;
    if ((!hasText && !hasImgs) || loading) return;
    const text = input || "(image attached)";
    const imgsForTurn = followImages;
    setInput("");
    setFollowImages([]);
    setMessages((m) => [...m, { role: "user", text, images: imgsForTurn }]);
    setLoading(true);
    try {
      const { data } = await api.post("/ai/help", {
        problem,
        message: text,
        grade_level: gradeLevel,
        subject: subject || null,
        session_id: sessionId,
        images: imgsForTurn.length ? imgsForTurn : null,
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
    setProblemImages([]);
    setFollowImages([]);
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
            Paste a question — or a screenshot of one. Learnify won't just give you the answer. It asks what you don't understand, then teaches that bit. You finish the problem yourself.
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
                value={problem}
                onChange={(e) => setProblem(e.target.value)}
                onPaste={onPasteProblem}
                rows={5}
                placeholder="e.g., Expand and simplify (2x − 3)(x + 4) — or paste a screenshot (Ctrl/Cmd + V)"
                className="mt-2 brutal-input w-full font-mono text-sm"
              />
            </label>

            <ImageChips
              images={problemImages}
              onRemove={(i) => setProblemImages((cur) => cur.filter((_, k) => k !== i))}
              testIdPrefix="help-problem-image"
            />

            <div className="flex flex-wrap items-center gap-2">
              <input
                ref={problemFileRef}
                type="file"
                accept="image/*"
                multiple
                className="hidden"
                onChange={(e) => { pickProblemFiles(e.target.files); e.target.value = ""; }}
                data-testid="help-problem-file-input"
              />
              <button
                type="button"
                onClick={() => problemFileRef.current?.click()}
                className="brutal-btn bg-white hover:bg-butter inline-flex items-center gap-2 text-sm"
                data-testid="help-problem-attach-btn"
              >
                <ImageIcon size={16} weight="bold" /> Attach image
              </button>
              <span className="text-xs text-[#4A4A4A]">
                or press <kbd className="border-2 border-ink rounded px-1.5 py-0.5 text-[10px] font-mono">Ctrl/Cmd + V</kbd> to paste a screenshot
              </span>
            </div>

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
              <Warning size={12} className="inline mb-0.5" /> Tip: paste the FULL question so it has all the numbers/wording — or a clear photo of the worksheet.
            </p>
          </form>
        )}

        {inSession && (
          <div className="brutal-card p-5 bg-butter" data-testid="help-problem-display">
            <div className="text-xs uppercase tracking-[0.2em] font-bold mb-2">Your problem</div>
            <div className="font-mono text-sm whitespace-pre-wrap">{problem}</div>
            {problemImages.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {problemImages.map((src, i) => (
                  <img key={i} src={src} alt={`problem-${i}`} className="h-16 w-16 object-cover border-2 border-ink rounded-md" />
                ))}
              </div>
            )}
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
                    {m.images?.length > 0 && (
                      <div className="flex flex-wrap gap-2 mb-2">
                        {m.images.map((src, k) => (
                          <img key={k} src={src} alt={`msg-img-${k}`} className="h-20 w-20 object-cover border-2 border-white/40 rounded-md" />
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

            <ImageChips
              images={followImages}
              onRemove={(i) => setFollowImages((cur) => cur.filter((_, k) => k !== i))}
              testIdPrefix="help-follow-image"
              className="mt-3"
            />

            <form onSubmit={sendFollowUp} className="flex gap-2 border-t-2 border-ink pt-3 mt-3">
              <input
                data-testid="help-followup-input"
                value={input} onChange={(e) => setInput(e.target.value)}
                onPaste={onPasteFollow}
                placeholder="Reply — say what part you don't get, or paste an image…"
                className="brutal-input flex-1"
                disabled={loading}
              />
              <input
                ref={followFileRef}
                type="file"
                accept="image/*"
                multiple
                className="hidden"
                onChange={(e) => { pickFollowFiles(e.target.files); e.target.value = ""; }}
                data-testid="help-follow-file-input"
              />
              <button
                type="button"
                onClick={() => followFileRef.current?.click()}
                className="brutal-btn bg-white hover:bg-butter"
                title="Attach image"
                data-testid="help-follow-attach-btn"
              >
                <ImageIcon size={16} weight="bold" />
              </button>
              <button data-testid="help-followup-send" type="submit" disabled={loading || (!input.trim() && followImages.length === 0)}
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
            <strong>How this works:</strong> Learnify uses Socratic teaching. It restates the problem, asks what's confusing you, then teaches just that piece. You always finish the question yourself — that's how the learning sticks. {" "}
            <Link to="/pricing" className="font-bold underline underline-offset-4">Upgrade your plan</Link> for unlimited daily use.
          </div>
        )}
      </div>
    </AppLayout>
  );
}

function ImageChips({ images, onRemove, testIdPrefix, className = "" }) {
  if (!images?.length) return null;
  return (
    <div className={`flex flex-wrap gap-2 ${className}`} data-testid={`${testIdPrefix}-chips`}>
      {images.map((src, i) => (
        <div key={i} className="relative">
          <img src={src} alt={`attach-${i}`} className="h-16 w-16 object-cover border-2 border-ink rounded-md" data-testid={`${testIdPrefix}-${i}`} />
          <button
            type="button"
            onClick={() => onRemove(i)}
            className="absolute -top-2 -right-2 bg-ink text-white rounded-full border-2 border-white p-0.5 hover:bg-focus"
            data-testid={`${testIdPrefix}-remove-${i}`}
            aria-label="Remove image"
          >
            <X size={12} weight="bold" />
          </button>
        </div>
      ))}
    </div>
  );
}
