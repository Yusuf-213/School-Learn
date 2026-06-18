import { useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { Chat, PaperPlaneTilt, CheckCircle } from "@phosphor-icons/react";
import { toast } from "sonner";

const CATEGORIES = [
  { id: "feature", label: "Feature idea" },
  { id: "bug", label: "Bug / not working" },
  { id: "content", label: "Content / lesson" },
  { id: "other", label: "Other" },
];

export default function Suggestions() {
  const [category, setCategory] = useState("feature");
  const [message, setMessage] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!message.trim()) { toast.error("Write something first."); return; }
    setLoading(true);
    try {
      await api.post("/suggestions", { category, message });
      setSent(true);
      setMessage("");
    } catch (ex) {
      toast.error(ex.response?.data?.detail || "Failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout>
      <div className="max-w-2xl space-y-6" data-testid="suggestions-page">
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
              <div className="text-sm">The owner sees this in the HQ panel. We'll act on the patterns.</div>
            </div>
          </div>
        )}

        <form onSubmit={submit} className="brutal-card p-5 space-y-4">
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
              placeholder="What would make Learnify a 10/10 for you?"
              className="mt-2 brutal-input w-full" />
          </label>
          <button type="submit" disabled={loading} data-testid="suggestion-send-btn"
            className="brutal-btn bg-ink text-white inline-flex items-center gap-2 disabled:opacity-60">
            <PaperPlaneTilt size={16} weight="bold" /> {loading ? "Sending…" : "Send suggestion"}
          </button>
        </form>
      </div>
    </AppLayout>
  );
}
