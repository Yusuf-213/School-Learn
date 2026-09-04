import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Plus } from "@phosphor-icons/react";

export default function PromoCodesPanel() {
  const [codes, setCodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ code: "", kind: "lifetime_free", tier: "school_small", max_uses: "", days: "", expires_at: "", notes: "" });
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/owner/promo_codes");
      setCodes(data.codes || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not load codes");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const createCode = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      const payload = {
        code: form.code.trim().toUpperCase(),
        kind: form.kind,
        tier: form.tier,
        max_uses: form.max_uses ? Number(form.max_uses) : null,
        days: form.kind === "days_free" && form.days ? Number(form.days) : null,
        expires_at: form.expires_at || null,
        notes: form.notes || null,
      };
      await api.post("/owner/promo_codes", payload);
      toast.success(`Code ${payload.code} created`);
      setForm({ code: "", kind: "lifetime_free", tier: "school_small", max_uses: "", days: "", expires_at: "", notes: "" });
      load();
    } catch (ex) {
      toast.error(ex?.response?.data?.detail || "Could not create code");
    } finally {
      setCreating(false);
    }
  };

  const toggleActive = async (code, active) => {
    try {
      await api.patch(`/owner/promo_codes/${code}`, { active });
      load();
    } catch (ex) {
      toast.error(ex?.response?.data?.detail || "Update failed");
    }
  };

  return (
    <div className="space-y-6" data-testid="promo-panel">
      <section className="brutal-card p-6 bg-butter">
        <div className="flex items-center gap-2 mb-4">
          <Plus size={20} weight="bold" />
          <h2 className="font-display font-bold text-xl">Mint a new promo code</h2>
        </div>
        <form onSubmit={createCode} className="grid sm:grid-cols-2 gap-3">
          <label className="block sm:col-span-2">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Code</span>
            <input required data-testid="promo-code-input" value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
              className="mt-2 brutal-input w-full font-mono tracking-widest uppercase" placeholder="EARLYBIRD26" />
          </label>
          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Kind</span>
            <select data-testid="promo-kind-select" value={form.kind}
              onChange={(e) => setForm({ ...form, kind: e.target.value })}
              className="mt-2 brutal-input w-full">
              <option value="lifetime_free">Lifetime free</option>
              <option value="days_free">Free for N days</option>
            </select>
          </label>
          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Tier granted</span>
            <select data-testid="promo-tier-select" value={form.tier}
              onChange={(e) => setForm({ ...form, tier: e.target.value })}
              className="mt-2 brutal-input w-full">
              <option value="school_small">School · Small</option>
              <option value="school_medium">School · Medium</option>
              <option value="school_large">School · Large</option>
            </select>
          </label>
          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Max uses (blank = unlimited)</span>
            <input type="number" min={1} data-testid="promo-max-uses" value={form.max_uses}
              onChange={(e) => setForm({ ...form, max_uses: e.target.value })}
              className="mt-2 brutal-input w-full" placeholder="e.g. 10" />
          </label>
          {form.kind === "days_free" && (
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Days of free access</span>
              <input type="number" min={1} data-testid="promo-days" value={form.days}
                onChange={(e) => setForm({ ...form, days: e.target.value })}
                className="mt-2 brutal-input w-full" placeholder="e.g. 90" />
            </label>
          )}
          <label className="block sm:col-span-2">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Expires on (optional)</span>
            <input type="date" data-testid="promo-expires" value={form.expires_at}
              onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
              className="mt-2 brutal-input w-full" />
          </label>
          <label className="block sm:col-span-2">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Notes (internal)</span>
            <input data-testid="promo-notes" value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className="mt-2 brutal-input w-full" placeholder="e.g. Trust XYZ partnership" />
          </label>
          <div className="sm:col-span-2">
            <button type="submit" disabled={creating} data-testid="promo-create-btn"
              className="brutal-btn bg-ink text-white inline-flex items-center gap-2 disabled:opacity-60">
              <Plus size={16} weight="bold" /> {creating ? "Creating…" : "Create code"}
            </button>
          </div>
        </form>
      </section>

      <section>
        <h2 className="font-display font-extrabold text-2xl tracking-tight mb-4">All promo codes</h2>
        {loading ? (
          <div className="brutal-card p-6 text-[#4A4A4A]">Loading…</div>
        ) : (
          <div className="overflow-x-auto brutal-card">
            <table className="min-w-full text-sm">
              <thead className="bg-mint border-b-2 border-ink">
                <tr>
                  <th className="text-left p-3 font-display">Code</th>
                  <th className="text-left p-3 font-display">Kind</th>
                  <th className="text-left p-3 font-display">Tier</th>
                  <th className="text-right p-3 font-display">Uses</th>
                  <th className="text-left p-3 font-display">Expires</th>
                  <th className="text-left p-3 font-display">Status</th>
                  <th className="text-left p-3 font-display">Notes</th>
                  <th className="p-3"></th>
                </tr>
              </thead>
              <tbody>
                {codes.map((c) => (
                  <tr key={c.code} className="border-t border-ink/20" data-testid={`promo-row-${c.code}`}>
                    <td className="p-3 font-mono font-bold">{c.code}{c.builtin && <span className="ml-2 text-xs bg-butter border border-ink px-1 rounded">built-in</span>}</td>
                    <td className="p-3">{c.kind === "days_free" ? `${c.days || "?"} days free` : "Lifetime free"}</td>
                    <td className="p-3">{c.tier}</td>
                    <td className="p-3 text-right font-mono">
                      {c.uses ?? 0}{c.max_uses ? ` / ${c.max_uses}` : ""}
                    </td>
                    <td className="p-3 text-xs text-[#4A4A4A]">{c.expires_at ? new Date(c.expires_at).toLocaleDateString() : "—"}</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 border-2 border-ink rounded-md text-xs font-bold uppercase ${c.active ? "bg-mint" : "bg-peach"}`}>
                        {c.active ? "Active" : "Disabled"}
                      </span>
                    </td>
                    <td className="p-3 text-xs">{c.notes || "—"}</td>
                    <td className="p-3">
                      {!c.builtin && (
                        <button onClick={() => toggleActive(c.code, !c.active)}
                          data-testid={`promo-toggle-${c.code}`}
                          className="text-xs underline">
                          {c.active ? "Disable" : "Enable"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {codes.length === 0 && (
                  <tr><td colSpan={8} className="p-6 text-center text-[#4A4A4A]">No promo codes yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
