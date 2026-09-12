import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { Sparkle, Compass, ArrowsClockwise, Star, Path, PencilSimple, Trash, X } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Dreams() {
  const [dream, setDream] = useState("");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [current, setCurrent] = useState(null);

  const load = async () => {
    try {
      const { data } = await api.get("/student/dreams");
      setItems(data.items);
      if (data.items[0]) setCurrent(data.items[0]);
    } catch {}
  };
  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    if (!dream.trim()) { toast.error("Tell us your dream first."); return; }
    setLoading(true);
    try {
      const { data } = await api.post("/student/dreams", { dream });
      setCurrent(data);
      setItems((it) => [data, ...it]);
      setDream("");
      toast.success("Path mapped.");
    } catch (ex) {
      toast.error(ex.response?.data?.detail || "Failed");
    } finally {
      setLoading(false);
    }
  };

  const editDream = async (dreamId, newDream) => {
    try {
      const { data } = await api.patch(`/student/dreams/${dreamId}`, { dream: newDream });
      setCurrent(data);
      setItems((it) => it.map((x) => x.dream_id === dreamId ? data : x));
      toast.success("Dream updated — fresh route mapped.");
      return true;
    } catch (ex) {
      toast.error(ex.response?.data?.detail || "Failed");
      return false;
    }
  };

  const deleteDream = async (dreamId) => {
    if (!window.confirm("Delete this dream and its plan?")) return;
    try {
      await api.delete(`/student/dreams/${dreamId}`);
      setItems((it) => {
        const next = it.filter((x) => x.dream_id !== dreamId);
        setCurrent(next[0] || null);
        return next;
      });
      toast.success("Dream deleted.");
    } catch (ex) {
      toast.error(ex.response?.data?.detail || "Failed");
    }
  };

  return (
    <AppLayout>
      <div className="space-y-6 max-w-4xl" data-testid="dreams-page">
        <div className="flex items-center gap-3">
          <Compass size={28} weight="duotone" />
          <div>
            <div className="text-xs tracking-[0.2em] uppercase font-bold text-[#4A4A4A]">Dreams</div>
            <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Where are you headed?</h1>
          </div>
        </div>
        <p className="text-[#4A4A4A] max-w-2xl">
          Tell Learnify what you want to become — and we'll map the route. Change your mind any time — hit
          <strong> Edit</strong> on any past dream and the AI will build a fresh plan around your new direction.
        </p>

        <form onSubmit={submit} className="brutal-card p-5 bg-butter space-y-3">
          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">My dream</span>
            <textarea data-testid="dream-input" required rows={3} value={dream} onChange={(e) => setDream(e.target.value)}
              placeholder="e.g., Become a neurosurgeon · Work in game design · Open a bakery in Manchester · Be an Olympic sprinter"
              className="mt-2 brutal-input w-full" />
          </label>
          <button type="submit" disabled={loading} data-testid="dream-submit-btn" className="brutal-btn bg-ink text-white inline-flex items-center gap-2 disabled:opacity-60">
            <Sparkle size={16} weight="bold" /> {loading ? "Mapping…" : "Map my path"}
          </button>
        </form>

        {current?.plan && (
          <DreamPlan
            dream={current}
            onEdit={editDream}
            onDelete={deleteDream}
          />
        )}

        {items.length > 1 && (
          <section>
            <div className="text-xs uppercase tracking-[0.2em] font-bold mb-3">Past dreams</div>
            <div className="space-y-2">
              {items.filter((d) => d.dream_id !== current?.dream_id).map((d) => (
                <button key={d.dream_id} onClick={() => setCurrent(d)} className="brutal-card p-3 bg-white w-full text-left flex items-center gap-3" data-testid={`dream-row-${d.dream_id}`}>
                  <Star size={18} weight="duotone" />
                  <div className="flex-1">
                    <div className="text-sm font-bold truncate">{d.dream}</div>
                    <div className="text-xs text-[#4A4A4A]">{new Date(d.created_at).toLocaleDateString()}</div>
                  </div>
                </button>
              ))}
            </div>
          </section>
        )}
      </div>
    </AppLayout>
  );
}

function DreamPlan({ dream, onEdit, onDelete }) {
  const p = dream.plan;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(dream.dream);
  const [saving, setSaving] = useState(false);

  useEffect(() => { setDraft(dream.dream); }, [dream.dream_id]);

  const save = async () => {
    if (!draft.trim()) { toast.error("Dream can't be empty."); return; }
    if (draft === dream.dream) { setEditing(false); return; }
    setSaving(true);
    const ok = await onEdit(dream.dream_id, draft);
    setSaving(false);
    if (ok) setEditing(false);
  };

  return (
    <div className="brutal-card p-6 bg-white space-y-4" data-testid="dream-plan">
      <div className="flex justify-between items-start gap-3">
        <div className="flex-1">
          <div className="text-xs uppercase tracking-[0.2em] font-bold">Your dream</div>
          {editing ? (
            <div className="mt-2 space-y-2">
              <textarea
                rows={2}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                className="brutal-input w-full text-lg"
                data-testid="dream-edit-input"
                disabled={saving}
              />
              <div className="flex gap-2">
                <button onClick={save} disabled={saving} data-testid="dream-edit-save"
                  className="brutal-btn bg-ink text-white inline-flex items-center gap-2 text-sm disabled:opacity-60">
                  <ArrowsClockwise size={14} weight="bold" className={saving ? "animate-spin" : ""} />
                  {saving ? "Re-mapping…" : "Save & re-map route"}
                </button>
                <button onClick={() => { setEditing(false); setDraft(dream.dream); }}
                  disabled={saving} className="brutal-btn bg-white inline-flex items-center gap-2 text-sm">
                  <X size={14} /> Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="font-display font-bold text-xl mt-1">{dream.dream}</div>
          )}
        </div>
        {!editing && (
          <div className="flex gap-2 shrink-0">
            <button onClick={() => setEditing(true)} data-testid="dream-edit-btn"
              className="brutal-btn bg-butter hover:bg-white inline-flex items-center gap-1 text-sm py-1.5 px-2">
              <PencilSimple size={14} weight="bold" /> Edit
            </button>
            <button onClick={() => onDelete(dream.dream_id)} data-testid="dream-delete-btn"
              className="brutal-btn bg-white hover:bg-peach inline-flex items-center gap-1 text-sm py-1.5 px-2">
              <Trash size={14} weight="bold" /> Delete
            </button>
          </div>
        )}
      </div>
      <div className="border-2 border-ink rounded-md p-4 bg-mint">
        <strong>Summary:</strong> {p.summary}
      </div>
      <div className="grid sm:grid-cols-2 gap-3">
        <div className="border-2 border-ink rounded-md p-3 bg-butter">
          <div className="text-xs uppercase tracking-[0.2em] font-bold mb-2">Subjects to focus on</div>
          <ul className="list-disc pl-5 text-sm space-y-1">{p.subjects_to_focus?.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
        <div className="border-2 border-ink rounded-md p-3 bg-lavender">
          <div className="text-xs uppercase tracking-[0.2em] font-bold mb-2">Extracurriculars</div>
          <ul className="list-disc pl-5 text-sm space-y-1">{p.extracurricular?.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      </div>
      {p.qualifications?.length > 0 && (
        <div className="border-2 border-ink rounded-md p-3 bg-white">
          <div className="text-xs uppercase tracking-[0.2em] font-bold mb-2">Qualifications</div>
          <ul className="space-y-2 text-sm">
            {p.qualifications.map((q, i) => (
              <li key={i}><strong>{q.stage}:</strong> {q.details}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="border-2 border-ink rounded-md p-3 bg-peach">
        <div className="text-xs uppercase tracking-[0.2em] font-bold mb-2 flex items-center gap-1"><Path size={14} weight="bold" /> First 3 steps</div>
        <ol className="list-decimal pl-5 text-sm space-y-1">{p.first_3_steps?.map((s, i) => <li key={i}>{s}</li>)}</ol>
      </div>
      {p.backup_paths?.length > 0 && (
        <div className="border-2 border-ink rounded-md p-3 bg-sky-100" data-testid="dream-backup-paths">
          <div className="text-xs uppercase tracking-[0.2em] font-bold mb-2">Backup paths</div>
          <ul className="list-disc pl-5 text-sm space-y-1">{p.backup_paths.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      )}
      {p.realistic_challenges?.length > 0 && (
        <details className="border-2 border-ink rounded-md p-3 bg-white">
          <summary className="text-xs uppercase tracking-[0.2em] font-bold cursor-pointer">Realistic challenges</summary>
          <ul className="list-disc pl-5 text-sm space-y-1 mt-2">{p.realistic_challenges.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </details>
      )}
      {p.timeframe_years > 0 && (
        <div className="text-sm text-[#4A4A4A]">Estimated timeframe: <strong className="text-ink">{p.timeframe_years} years</strong></div>
      )}
      {dream.history?.length > 0 && (
        <div className="text-xs text-[#4A4A4A] pt-2 border-t border-ink/20" data-testid="dream-history-count">
          {dream.history.length} previous version{dream.history.length > 1 ? "s" : ""} archived.
        </div>
      )}
    </div>
  );
}
