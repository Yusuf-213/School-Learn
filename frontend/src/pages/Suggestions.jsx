import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Chat, PaperPlaneTilt, CheckCircle, Users, User, ThumbsUp, ThumbsDown, ShieldCheck, ChalkboardTeacher } from "@phosphor-icons/react";
import { toast } from "sonner";

const CATEGORIES = [
  { id: "feature", label: "Feature idea" },
  { id: "bug", label: "Bug / not working" },
  { id: "content", label: "Content / lesson" },
  { id: "other", label: "Other" },
];

export default function Suggestions() {
  const { user } = useAuth();
  const [category, setCategory] = useState("feature");
  const [scope, setScope] = useState("individual");
  const [message, setMessage] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [pending, setPending] = useState([]);

  const canCosign = user?.role === "student" || user?.role === "teacher";
  const inSchool = !!user?.school_id;

  const loadPending = async () => {
    if (!inSchool && user?.role !== "owner") { setPending([]); return; }
    try {
      const { data } = await api.get("/suggestions/pending");
      setPending(data.items || []);
    } catch { setPending([]); }
  };
  useEffect(() => { loadPending(); /* eslint-disable-next-line */ }, [user?.user_id]);

  const submit = async (e) => {
    e.preventDefault();
    if (!message.trim()) { toast.error("Write something first."); return; }
    setLoading(true);
    try {
      await api.post("/suggestions", { category, message, scope });
      setSent(true);
      setMessage("");
      if (scope === "school") {
        toast.success("Sent to your school. It reaches the owner once 2 students + 2 teachers co-sign.");
        loadPending();
      } else {
        toast.success("Sent straight to the owner's inbox.");
      }
    } catch (ex) {
      toast.error(ex.response?.data?.detail || "Failed");
    } finally {
      setLoading(false);
    }
  };

  const cosign = async (id, agree) => {
    try {
      const { data } = await api.post(`/suggestions/${id}/cosign`, { agree });
      if (data.just_escalated) {
        toast.success("Escalated — the owner now sees this suggestion.");
      } else {
        toast.success(agree ? "Vote recorded." : "Vote withdrawn.");
      }
      loadPending();
    } catch (ex) {
      toast.error(ex.response?.data?.detail || "Failed");
    }
  };

  return (
    <AppLayout>
      <div className="max-w-3xl space-y-6" data-testid="suggestions-page">
        <div className="flex items-center gap-3">
          <Chat size={28} weight="duotone" />
          <div>
            <div className="text-xs tracking-[0.2em] uppercase font-bold text-[#4A4A4A]">Suggestions</div>
            <h1 className="font-display font-black text-4xl tracking-tight">Tell us what to build next.</h1>
          </div>
        </div>

        {sent && (
          <div className="brutal-card p-5 bg-mint flex items-center gap-3" data-testid="suggestion-sent">
            <CheckCircle size={24} weight="fill" />
            <div>
              <div className="font-bold">Thanks — we read everything.</div>
              <div className="text-sm">
                {scope === "school"
                  ? "Now waiting for 2 students + 2 teachers at your school to co-sign before it reaches the owner."
                  : "It's already in the owner's inbox."}
              </div>
            </div>
          </div>
        )}

        <form onSubmit={submit} className="brutal-card p-5 space-y-4">
          <div>
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Who's it from?</span>
            <div className="grid sm:grid-cols-2 gap-2 mt-2">
              <button type="button" onClick={() => setScope("individual")} data-testid="scope-individual"
                className={`brutal-card p-3 text-left ${scope === "individual" ? "bg-ink text-white" : "bg-white hover:bg-butter"}`}>
                <div className="flex items-center gap-2"><User size={16} weight="bold" /> <strong>Just me</strong></div>
                <div className={`text-xs mt-1 ${scope === "individual" ? "text-white/80" : "text-[#4A4A4A]"}`}>
                  Straight to the owner. No co-signatures needed.
                </div>
              </button>
              <button type="button" onClick={() => setScope("school")} disabled={!inSchool} data-testid="scope-school"
                className={`brutal-card p-3 text-left ${scope === "school" ? "bg-ink text-white" : "bg-white hover:bg-butter"} ${!inSchool ? "opacity-50" : ""}`}>
                <div className="flex items-center gap-2"><Users size={16} weight="bold" /> <strong>School-wide</strong></div>
                <div className={`text-xs mt-1 ${scope === "school" ? "text-white/80" : "text-[#4A4A4A]"}`}>
                  Needs 2 students + 2 teachers to co-sign before the owner sees it.
                  {!inSchool && " Join a school to use this."}
                </div>
              </button>
            </div>
          </div>

          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Category</span>
            <div className="flex flex-wrap gap-2 mt-2">
              {CATEGORIES.map((c) => (
                <button type="button" key={c.id} onClick={() => setCategory(c.id)}
                  data-testid={`suggestion-cat-${c.id}`}
                  className={`brutal-btn text-sm ${category === c.id ? "bg-ink text-white" : "bg-white hover:bg-butter"}`}>
                  {c.label}
                </button>
              ))}
            </div>
          </label>
          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Your suggestion</span>
            <textarea data-testid="suggestion-message-input" required rows={5} value={message}
              onChange={(e) => { setMessage(e.target.value); setSent(false); }}
              placeholder="What would make Learnify a 10/10 for your school?"
              className="mt-2 brutal-input w-full" />
          </label>
          <button type="submit" disabled={loading} data-testid="suggestion-send-btn"
            className="brutal-btn bg-ink text-white inline-flex items-center gap-2 disabled:opacity-60">
            <PaperPlaneTilt size={16} weight="bold" /> {loading ? "Sending…" : (scope === "school" ? "Send to school for co-sign" : "Send to owner")}
          </button>
        </form>

        {inSchool && (
          <section data-testid="pending-cosign-section">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-display font-extrabold text-2xl">School suggestions waiting for co-signs</h2>
              <span className="text-xs text-[#4A4A4A]">{pending.length} open</span>
            </div>
            {pending.length === 0 ? (
              <div className="brutal-card p-6 text-[#4A4A4A]">No open school suggestions. Start one above.</div>
            ) : (
              <div className="space-y-3">
                {pending.map((s) => (
                  <div key={s.suggestion_id} className="brutal-card p-4 bg-white" data-testid={`pending-${s.suggestion_id}`}>
                    <div className="flex items-start justify-between gap-3 flex-wrap">
                      <div className="flex-1 min-w-[220px]">
                        <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">
                          {s.category} · from {s.user_name || s.user_email}
                        </div>
                        <div className="text-sm mt-1 whitespace-pre-line">{s.message}</div>
                      </div>
                      <div className="text-xs text-[#4A4A4A] shrink-0">{new Date(s.created_at).toLocaleDateString()}</div>
                    </div>
                    <div className="mt-3 grid sm:grid-cols-2 gap-2">
                      <div className="border-2 border-ink rounded-md p-2 bg-mint/60 text-xs font-bold flex items-center gap-2">
                        <Users size={14} weight="bold" /> Students: {s.student_cosigns}/2 {s.needs_students === 0 && <ShieldCheck size={14} weight="fill" />}
                      </div>
                      <div className="border-2 border-ink rounded-md p-2 bg-butter/70 text-xs font-bold flex items-center gap-2">
                        <ChalkboardTeacher size={14} weight="bold" /> Teachers: {s.teacher_cosigns}/2 {s.needs_teachers === 0 && <ShieldCheck size={14} weight="fill" />}
                      </div>
                    </div>
                    {canCosign && (
                      <div className="mt-3 flex gap-2">
                        <button onClick={() => cosign(s.suggestion_id, true)} disabled={!!s.my_vote}
                          data-testid={`cosign-agree-${s.suggestion_id}`}
                          className="brutal-btn bg-ink text-white text-sm inline-flex items-center gap-2 disabled:opacity-60">
                          <ThumbsUp size={14} weight="bold" /> {s.my_vote ? "Agreed ✓" : "I agree — co-sign"}
                        </button>
                        {s.my_vote && (
                          <button onClick={() => cosign(s.suggestion_id, false)}
                            data-testid={`cosign-withdraw-${s.suggestion_id}`}
                            className="brutal-btn bg-white hover:bg-peach text-sm inline-flex items-center gap-2">
                            <ThumbsDown size={14} weight="bold" /> Withdraw
                          </button>
                        )}
                      </div>
                    )}
                    {!canCosign && (
                      <div className="mt-3 text-xs text-[#4A4A4A]">Only students and teachers can co-sign school suggestions.</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </div>
    </AppLayout>
  );
}
