import { useEffect, useRef, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { Timer, Play, X, Warning, Globe, Lock, CheckCircle } from "@phosphor-icons/react";
import { toast } from "sonner";

const PRESETS = [10, 25, 45, 60, 90];

export default function Focus() {
  const [active, setActive] = useState(null);
  const [history, setHistory] = useState([]);
  const [task, setTask] = useState("");
  const [duration, setDuration] = useState(25);
  const [blockedSite, setBlockedSite] = useState("");
  const [loading, setLoading] = useState(false);

  const load = async () => {
    try {
      const [a, h] = await Promise.all([api.get("/focus/active"), api.get("/focus/history")]);
      setActive(a.data.active);
      setHistory(h.data.items || []);
    } catch {}
  };

  useEffect(() => { load(); }, []);

  const start = async (e) => {
    e.preventDefault();
    if (!task.trim()) return toast.error("Tell us what you'll focus on.");
    setLoading(true);
    try {
      const { data } = await api.post("/focus/start", {
        duration_minutes: duration,
        task,
        blocked_site: blockedSite || null,
      });
      setActive(data);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to start session");
    } finally {
      setLoading(false);
    }
  };

  if (active) return <FocusSession session={active} onEnd={() => { setActive(null); load(); }} />;

  return (
    <AppLayout>
      <div className="max-w-3xl space-y-8">
        <div>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A]">Focus Mode</div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Lock in. Get it done.</h1>
          <p className="text-[#4A4A4A] mt-3 max-w-xl">Pick a task and timer. We'll hide everything else and warn you if you try to leave. No tab-switching escape route.</p>
        </div>

        <form onSubmit={start} className="brutal-card p-8 space-y-5">
          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">What are you focusing on?</span>
            <input
              data-testid="focus-task-input"
              required value={task} onChange={(e) => setTask(e.target.value)}
              placeholder="e.g., Review Algebra: quadratics"
              className="mt-2 brutal-input w-full"
            />
          </label>

          <div>
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Duration</span>
            <div className="flex flex-wrap gap-2 mt-2">
              {PRESETS.map((m) => (
                <button
                  type="button" key={m}
                  onClick={() => setDuration(m)}
                  data-testid={`duration-preset-${m}`}
                  className={`brutal-btn text-sm ${duration === m ? "bg-ink text-white" : "bg-white hover:bg-butter"}`}
                >
                  {m} min
                </button>
              ))}
              <input
                type="number" min={1} max={240} value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
                className="brutal-input w-24"
                data-testid="duration-custom-input"
              />
            </div>
          </div>

          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold flex items-center gap-2"><Globe size={14} /> Site/app to avoid (optional reminder)</span>
            <input
              data-testid="focus-blocked-input"
              value={blockedSite} onChange={(e) => setBlockedSite(e.target.value)}
              placeholder="e.g., youtube.com"
              className="mt-2 brutal-input w-full"
            />
            <span className="text-xs text-[#4A4A4A] mt-1 inline-block">
              Heads up: we can't truly block other sites from inside a browser, but we'll log it and remind you not to visit.
            </span>
          </label>

          <button
            type="submit" disabled={loading}
            data-testid="focus-start-btn"
            className="brutal-btn bg-ink text-white w-full inline-flex items-center justify-center gap-2 disabled:opacity-60"
          >
            <Play size={18} weight="fill" /> {loading ? "Starting…" : `Start ${duration}-minute focus`}
          </button>
        </form>

        {history.length > 0 && (
          <section>
            <h2 className="font-display font-extrabold text-2xl tracking-tight mb-4">Recent sessions</h2>
            <div className="space-y-2">
              {history.slice(0, 6).map((h) => (
                <div key={h.session_id} className="brutal-card p-4 flex items-center justify-between" data-testid={`history-${h.session_id}`}>
                  <div>
                    <div className="font-bold">{h.task}</div>
                    <div className="text-xs text-[#4A4A4A]">{h.duration_minutes} min · {new Date(h.started_at).toLocaleString()}</div>
                  </div>
                  <span className={`text-xs uppercase tracking-[0.2em] font-bold px-3 py-1 border-2 border-ink rounded-md ${
                    h.status === "completed" ? "bg-mint" : h.status === "active" ? "bg-butter" : "bg-peach"
                  }`}>{h.status}</span>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </AppLayout>
  );
}

function FocusSession({ session, onEnd }) {
  const [now, setNow] = useState(Date.now());
  const [tried, setTried] = useState(false);
  const endsAt = new Date(session.ends_at).getTime();
  const startedAt = new Date(session.started_at).getTime();
  const total = endsAt - startedAt;
  const remaining = Math.max(0, endsAt - now);
  const done = remaining === 0;

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (done) {
      api.post(`/focus/end/${session.session_id}`).catch(() => {});
    }
  }, [done, session.session_id]);

  // Warn on leaving page during active session
  useEffect(() => {
    const handler = (e) => {
      if (!done) {
        e.preventDefault();
        e.returnValue = "";
        return "";
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [done]);

  const mins = Math.floor(remaining / 60000);
  const secs = Math.floor((remaining % 60000) / 1000);
  const pct = total > 0 ? Math.max(0, Math.min(100, (remaining / total) * 100)) : 0;

  const endEarly = async () => {
    if (!window.confirm("Quit this focus session? You'll lose the streak for this session.")) return;
    try { await api.post(`/focus/end/${session.session_id}`); } catch {}
    onEnd();
  };

  return (
    <div className="fixed inset-0 bg-ink text-paper flex flex-col items-center justify-center p-6 z-50" data-testid="focus-active-overlay">
      <div className="absolute top-6 left-6 flex items-center gap-2 text-paper/70 text-xs uppercase tracking-[0.2em] font-bold">
        <Lock size={14} weight="bold" /> Focus locked
      </div>
      <button
        onClick={endEarly}
        data-testid="focus-end-btn"
        className="absolute top-6 right-6 border-2 border-paper rounded-md px-3 py-2 text-xs font-bold hover:bg-paper hover:text-ink transition-all flex items-center gap-2"
      >
        <X size={14} weight="bold" /> End early
      </button>

      <div className="text-xs uppercase tracking-[0.4em] font-bold text-paper/60 mb-3">Focusing on</div>
      <h1 className="font-display font-black text-3xl sm:text-5xl tracking-tight text-center max-w-3xl mb-12">
        {session.task}
      </h1>

      {!done ? (
        <>
          <div className="font-display font-black tabular-nums leading-none" style={{ fontSize: "min(20vw, 200px)" }} data-testid="focus-countdown">
            {String(mins).padStart(2, "0")}:{String(secs).padStart(2, "0")}
          </div>

          <div className="w-full max-w-xl mt-10">
            <div className="h-2 border-2 border-paper rounded-full overflow-hidden">
              <div className="h-full bg-paper transition-all duration-500" style={{ width: `${pct}%` }} />
            </div>
            <div className="text-xs uppercase tracking-[0.2em] font-bold text-paper/60 mt-3 text-center">
              {Math.round(pct)}% time remaining
            </div>
          </div>

          {session.blocked_site && (
            <div className="mt-10 border-2 border-paper rounded-md px-4 py-3 bg-paper/5 flex items-center gap-2 text-sm">
              <Warning size={16} weight="bold" /> You committed to avoid <strong className="ml-1">{session.blocked_site}</strong>.
            </div>
          )}

          <button
            onClick={() => setTried(true)}
            className="mt-8 text-xs text-paper/40 hover:text-paper underline underline-offset-4"
            data-testid="focus-distraction-btn"
          >
            I want to switch away
          </button>
          {tried && (
            <div className="mt-3 text-sm text-paper/80 max-w-sm text-center">
              Stay with it. {mins}m {secs}s left. The discomfort of focus is the price of progress.
            </div>
          )}
        </>
      ) : (
        <div className="text-center" data-testid="focus-complete">
          <CheckCircle size={64} weight="duotone" className="mx-auto mb-4" />
          <div className="font-display font-black text-5xl mb-3">Done.</div>
          <div className="text-paper/70 mb-8">You focused for {session.duration_minutes} minutes. That counts.</div>
          <button onClick={onEnd} className="brutal-btn bg-paper text-ink hover:bg-butter" data-testid="focus-back-btn">
            Back to dashboard
          </button>
        </div>
      )}
    </div>
  );
}
