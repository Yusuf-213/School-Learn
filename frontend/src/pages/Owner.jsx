import { useEffect, useState, useCallback } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Buildings, Users, BookOpen, Lightning, ChartLineUp, Chat, Crown, Ticket, ShieldCheck, DownloadSimple, Plus, Link as LinkIcon, Copy, Archive } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Owner() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [schools, setSchools] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [tab, setTab] = useState("overview");

  useEffect(() => {
    (async () => {
      try {
        const [s, sc, sg] = await Promise.all([
          api.get("/owner/stats"),
          api.get("/owner/schools"),
          api.get("/owner/suggestions"),
        ]);
        setStats(s.data);
        setSchools(sc.data.schools);
        setSuggestions(sg.data.items);
      } catch {}
    })();
  }, []);

  if (user?.role !== "owner") {
    return (
      <AppLayout>
        <div className="brutal-card p-8 max-w-md mx-auto">
          <Crown size={36} weight="duotone" />
          <h1 className="font-display font-black text-2xl mt-3">Owner panel</h1>
          <p className="text-[#4A4A4A] mt-2">Only the owner account can access this page.</p>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-8" data-testid="owner-page">
        <div>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A]">Owner panel</div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Learnify HQ.</h1>
          <p className="text-[#4A4A4A] mt-3">Everything across every school, in one view.</p>
        </div>

        <div className="flex flex-wrap gap-2 border-b-2 border-ink pb-3" data-testid="owner-tabs">
          <TabBtn active={tab === "overview"} onClick={() => setTab("overview")} testid="tab-overview">Overview</TabBtn>
          <TabBtn active={tab === "promo"} onClick={() => setTab("promo")} testid="tab-promo"><Ticket size={14} weight="bold" /> Promo Codes</TabBtn>
          <TabBtn active={tab === "links"} onClick={() => setTab("links")} testid="tab-links"><LinkIcon size={14} weight="bold" /> Payment Links</TabBtn>
          <TabBtn active={tab === "dpa"} onClick={() => setTab("dpa")} testid="tab-dpa"><ShieldCheck size={14} weight="bold" /> DPA Acceptances</TabBtn>
        </div>

        {tab === "overview" && (
          <>
            {stats && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Stat label="Schools" value={stats.schools} icon={Buildings} bg="bg-mint" tid="stat-schools" />
                <Stat label="Paying schools" value={stats.paying_schools} icon={Crown} bg="bg-butter" tid="stat-paying" />
                <Stat label="Students" value={stats.students} icon={Users} bg="bg-lavender" tid="stat-students" />
                <Stat label="Teachers" value={stats.teachers} icon={Users} bg="bg-peach" tid="stat-teachers" />
                <Stat label="Homework set" value={stats.homework} icon={BookOpen} bg="bg-white" tid="stat-homework" />
                <Stat label="Lessons planned" value={stats.lessons} icon={Lightning} bg="bg-white" tid="stat-lessons" />
                <Stat label="Dreams logged" value={stats.dreams} icon={ChartLineUp} bg="bg-white" tid="stat-dreams" />
                <Stat label="Suggestions" value={stats.suggestions} icon={Chat} bg="bg-white" tid="stat-suggestions" />
              </div>
            )}

            <section>
              <h2 className="font-display font-extrabold text-2xl tracking-tight mb-4">Schools</h2>
              {schools.length === 0 ? (
                <div className="brutal-card p-6 text-[#4A4A4A]">No schools have registered yet.</div>
              ) : (
                <div className="overflow-x-auto brutal-card">
                  <table className="min-w-full text-sm">
                    <thead className="bg-butter border-b-2 border-ink">
                      <tr>
                        <th className="text-left p-3 font-display">School</th>
                        <th className="text-left p-3 font-display">Domain</th>
                        <th className="text-left p-3 font-display">Plan</th>
                        <th className="text-right p-3 font-display">Students</th>
                        <th className="text-right p-3 font-display">Teachers</th>
                        <th className="text-right p-3 font-display">Classes</th>
                        <th className="text-right p-3 font-display">Homework</th>
                        <th className="text-left p-3 font-display">Joined</th>
                      </tr>
                    </thead>
                    <tbody>
                      {schools.map((s) => (
                        <tr key={s.school_id} className="border-t border-ink/20" data-testid={`owner-school-${s.school_id}`}>
                          <td className="p-3 font-bold">{s.name}</td>
                          <td className="p-3 text-[#4A4A4A]">@{s.email_domain}</td>
                          <td className="p-3">
                            <span className="px-2 py-0.5 border-2 border-ink rounded-md bg-mint text-xs font-bold uppercase">{s.subscription_tier || "free"}</span>
                          </td>
                          <td className="p-3 text-right font-mono">{s.student_count}</td>
                          <td className="p-3 text-right font-mono">{s.teacher_count}</td>
                          <td className="p-3 text-right font-mono">{s.classes_count}</td>
                          <td className="p-3 text-right font-mono">{s.homework_count}</td>
                          <td className="p-3 text-[#4A4A4A] text-xs">{new Date(s.created_at).toLocaleDateString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section>
              <h2 className="font-display font-extrabold text-2xl tracking-tight mb-4">Recent suggestions</h2>
              {suggestions.length === 0 ? (
                <div className="brutal-card p-6 text-[#4A4A4A]">Nothing in the inbox yet.</div>
              ) : (
                <div className="space-y-2">
                  {suggestions.slice(0, 20).map((s) => (
                    <div key={s.suggestion_id} className="brutal-card p-4 bg-white" data-testid={`owner-suggestion-${s.suggestion_id}`}>
                      <div className="flex justify-between items-start gap-3">
                        <div>
                          <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">{s.category}</div>
                          <div className="text-sm mt-1">{s.message}</div>
                        </div>
                        <div className="text-xs text-[#4A4A4A]">{s.user_name || s.user_email}<br />{new Date(s.created_at).toLocaleDateString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </>
        )}

        {tab === "promo" && <PromoCodesPanel />}
        {tab === "links" && <PaymentLinksPanel />}
        {tab === "dpa" && <DpaAcceptancesPanel />}
        {tab === "overview" && <BusinessPanel />}
      </div>
    </AppLayout>
  );
}

function TabBtn({ active, onClick, children, testid }) {
  return (
    <button
      onClick={onClick}
      data-testid={testid}
      className={`brutal-btn text-sm inline-flex items-center gap-1 ${active ? "bg-ink text-white" : "bg-white"}`}
    >
      {children}
    </button>
  );
}

function Stat({ label, value, icon: Icon, bg, tid }) {
  return (
    <div className={`brutal-card p-4 ${bg}`} data-testid={tid}>
      <div className="flex items-center justify-between mb-2">
        <Icon size={18} weight="duotone" />
      </div>
      <div className="font-display font-black text-2xl">{value}</div>
      <div className="text-xs tracking-[0.2em] uppercase font-bold mt-1">{label}</div>
    </div>
  );
}

// ---------------- Business + Stripe ----------------

function BusinessPanel() {
  const [pricing, setPricing] = useState(null);
  const [stripe, setStripe] = useState(null);
  useEffect(() => {
    api.get("/owner/business/pricing").then(({ data }) => setPricing(data)).catch(() => {});
    api.get("/owner/stripe/status").then(({ data }) => setStripe(data)).catch(() => {});
  }, []);
  return (
    <section className="mt-6 space-y-4" data-testid="business-panel">
      <h2 className="font-display font-extrabold text-2xl">Business — pricing tiers</h2>
      {pricing && (
        <>
          <div className="brutal-card p-5 bg-mint">
            <h3 className="font-display font-bold text-lg mb-2">Schools (annual, GBP)</h3>
            <ul className="text-sm space-y-1">
              {pricing.schools.map((r) => (
                <li key={r.tier} className="flex justify-between border-b border-ink/20 py-1" data-testid={`school-tier-${r.tier}`}>
                  <span><b>{r.tier}</b> · {r.students} students</span>
                  <span className="font-mono">£{r.annual_gbp.toLocaleString()}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="brutal-card p-5 bg-butter">
            <h3 className="font-display font-bold text-lg mb-2">Multi-Academy Trusts (annual, GBP)</h3>
            <ul className="text-sm space-y-1">
              {pricing.mats.map((r) => (
                <li key={r.tier} className="flex justify-between border-b border-ink/20 py-1" data-testid={`mat-tier-${r.tier.replace(/\s+/g, "-")}`}>
                  <span><b>{r.tier}</b></span>
                  <span className="font-mono">£{r.annual_gbp.toLocaleString()}</span>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
      {stripe && (
        <div className={`brutal-card p-5 ${stripe.connected ? "bg-mint" : "bg-peach"}`} data-testid="stripe-status">
          <h3 className="font-display font-bold text-lg">Stripe {stripe.connected ? "connected" : "not connected"}</h3>
          <p className="text-sm mt-1">Mode: <b>{stripe.mode}</b> · Key tail: <code>…{stripe.key_tail}</code> · Webhook: {stripe.webhook_configured ? "signed" : "unsigned"}</p>
          <p className="text-xs mt-2 text-[#4A4A4A]">{stripe.instructions}</p>
        </div>
      )}
    </section>
  );
}

function PromoCodesPanel() {
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

// ---------------- Owner custom Stripe payment links ----------------

const CATEGORY_PRESETS = [
  { id: "school_small",  name: "School · Small (600–1,000 students)",    suggested: 3000 },
  { id: "school_medium", name: "School · Medium (1,000–1,500 students)", suggested: 8000 },
  { id: "school_large",  name: "School · Large (1,500+ students)",       suggested: 15000 },
  { id: "mat_1_5",       name: "MAT · 1–5 schools",                       suggested: 200000 },
  { id: "mat_5_10",      name: "MAT · 5–10 schools",                      suggested: 400000 },
  { id: "mat_10_30",     name: "MAT · 10–30 schools",                     suggested: 600000 },
  { id: "mat_30_50",     name: "MAT · 30–50 schools",                     suggested: 800000 },
  { id: "mat_50_80",     name: "MAT · 50–80 schools",                     suggested: 1000000 },
  { id: "mat_80_100",    name: "MAT · 80–100 schools",                    suggested: 2000000 },
  { id: "custom",        name: "Custom / bespoke",                        suggested: "" },
];

function PaymentLinksPanel() {
  const [links, setLinks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [stripe, setStripe] = useState(null);
  const [form, setForm] = useState({
    label: "",
    category: "school_small",
    amount: 3000,
    customer_email: "",
    expires_in_days: 30,
    notes: "",
  });
  const [lastCreated, setLastCreated] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [{ data }, s] = await Promise.all([
        api.get("/owner/billing/payment-links"),
        api.get("/owner/stripe/status"),
      ]);
      setLinks(data.links || []);
      setStripe(s.data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not load payment links");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const onCategoryChange = (id) => {
    const preset = CATEGORY_PRESETS.find((c) => c.id === id);
    setForm((f) => ({
      ...f,
      category: id,
      amount: preset && preset.suggested !== "" ? preset.suggested : f.amount,
    }));
  };

  const createLink = async (e) => {
    e.preventDefault();
    const amt = Number(form.amount);
    if (!form.label.trim()) { toast.error("Label is required"); return; }
    if (!Number.isFinite(amt) || amt <= 0) { toast.error("Amount must be greater than 0"); return; }
    setCreating(true);
    try {
      const { data } = await api.post("/owner/billing/payment-link", {
        label: form.label.trim(),
        category: form.category,
        amount: amt,
        currency: "gbp",
        customer_email: form.customer_email || null,
        expires_in_days: form.expires_in_days ? Number(form.expires_in_days) : null,
        notes: form.notes || null,
      });
      setLastCreated(data);
      toast.success("Payment link created");
      setForm({ label: "", category: "school_small", amount: 3000, customer_email: "", expires_in_days: 30, notes: "" });
      load();
    } catch (ex) {
      toast.error(ex?.response?.data?.detail || "Could not create link");
    } finally {
      setCreating(false);
    }
  };

  const copyLink = async (url, id) => {
    try {
      await navigator.clipboard.writeText(url);
      toast.success("Link copied to clipboard");
    } catch {
      toast.error("Clipboard blocked — long-press to copy");
    }
  };

  const archive = async (link_id) => {
    try {
      await api.patch(`/owner/billing/payment-links/${link_id}`, { status: "archived" });
      load();
    } catch (ex) {
      toast.error(ex?.response?.data?.detail || "Could not archive");
    }
  };

  return (
    <div className="space-y-6" data-testid="payment-links-panel">
      {stripe && (
        <div className={`brutal-card p-4 ${stripe.mode === "live" ? "bg-mint" : "bg-butter"}`} data-testid="pl-stripe-mode">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div>
              <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">Stripe</div>
              <div className="font-display font-bold text-lg">
                {stripe.mode === "live" ? "Live mode — real charges" : stripe.mode === "test" ? "Test mode — no real charges" : "Not connected"}
                <span className="ml-2 text-[#4A4A4A] font-mono text-xs">…{stripe.key_tail}</span>
              </div>
              <p className="text-xs text-[#4A4A4A] mt-1">
                {stripe.mode === "live"
                  ? "Every link you create here will take a real card payment in GBP."
                  : "Set STRIPE_API_KEY to a sk_live_… key in Emergent Secrets to switch to live payments."}
              </p>
            </div>
          </div>
        </div>
      )}

      <section className="brutal-card p-6 bg-peach">
        <div className="flex items-center gap-2 mb-4">
          <LinkIcon size={20} weight="bold" />
          <h2 className="font-display font-bold text-xl">Generate a custom Stripe payment link</h2>
        </div>
        <p className="text-sm text-[#333] mb-4">
          Mint a bespoke checkout URL for a school or MAT that negotiated a custom price. Share it via email — the buyer pays in GBP via Stripe Checkout.
        </p>
        <form onSubmit={createLink} className="grid sm:grid-cols-2 gap-3">
          <label className="block sm:col-span-2">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Label (what this link is for)</span>
            <input required data-testid="pl-label" value={form.label}
              onChange={(e) => setForm({ ...form, label: e.target.value })}
              className="mt-2 brutal-input w-full" placeholder="e.g. St Mary's High · Bespoke annual licence 2026-27" />
          </label>
          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Category / preset</span>
            <select data-testid="pl-category" value={form.category}
              onChange={(e) => onCategoryChange(e.target.value)}
              className="mt-2 brutal-input w-full">
              {CATEGORY_PRESETS.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Amount (GBP £)</span>
            <input type="number" step="0.01" min="1" required data-testid="pl-amount" value={form.amount}
              onChange={(e) => setForm({ ...form, amount: e.target.value })}
              className="mt-2 brutal-input w-full font-mono" placeholder="e.g. 4500" />
          </label>
          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Customer email (optional)</span>
            <input type="email" data-testid="pl-email" value={form.customer_email}
              onChange={(e) => setForm({ ...form, customer_email: e.target.value })}
              className="mt-2 brutal-input w-full" placeholder="head@stmarys.sch.uk" />
          </label>
          <label className="block">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Expires in (days)</span>
            <input type="number" min="1" max="365" data-testid="pl-expires" value={form.expires_in_days}
              onChange={(e) => setForm({ ...form, expires_in_days: e.target.value })}
              className="mt-2 brutal-input w-full" placeholder="30" />
          </label>
          <label className="block sm:col-span-2">
            <span className="text-xs uppercase tracking-[0.2em] font-bold">Internal notes (optional)</span>
            <input data-testid="pl-notes" value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className="mt-2 brutal-input w-full" placeholder="Contract ref, MAT contact, follow-up date…" />
          </label>
          <div className="sm:col-span-2">
            <button type="submit" disabled={creating} data-testid="pl-create-btn"
              className="brutal-btn bg-ink text-white inline-flex items-center gap-2 disabled:opacity-60">
              <Plus size={16} weight="bold" /> {creating ? "Creating…" : "Create payment link"}
            </button>
          </div>
        </form>
      </section>

      {lastCreated && (
        <section className="brutal-card p-5 bg-mint" data-testid="pl-last-created">
          <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">Link ready — copy & send</div>
          <div className="font-display font-bold text-lg mt-1">{lastCreated.label}</div>
          <div className="text-sm text-[#333] mt-1">
            £{Number(lastCreated.amount).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} · {lastCreated.mode} mode · Session <code className="font-mono text-xs">{lastCreated.session_id?.slice(0, 12)}…</code>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <input readOnly value={lastCreated.url} className="brutal-input flex-1 min-w-[280px] font-mono text-xs" data-testid="pl-last-url" />
            <button onClick={() => copyLink(lastCreated.url)} data-testid="pl-copy-last"
              className="brutal-btn bg-white inline-flex items-center gap-2">
              <Copy size={14} weight="bold" /> Copy
            </button>
            <a href={lastCreated.url} target="_blank" rel="noreferrer" className="brutal-btn bg-ink text-white">Open</a>
          </div>
        </section>
      )}

      <section>
        <h2 className="font-display font-extrabold text-2xl tracking-tight mb-4">Payment links</h2>
        {loading ? (
          <div className="brutal-card p-6 text-[#4A4A4A]">Loading…</div>
        ) : links.length === 0 ? (
          <div className="brutal-card p-6 text-[#4A4A4A]">No links minted yet. Use the form above to create your first bespoke Stripe checkout URL.</div>
        ) : (
          <div className="overflow-x-auto brutal-card">
            <table className="min-w-full text-sm">
              <thead className="bg-butter border-b-2 border-ink">
                <tr>
                  <th className="text-left p-3 font-display">Created</th>
                  <th className="text-left p-3 font-display">Label</th>
                  <th className="text-left p-3 font-display">Category</th>
                  <th className="text-right p-3 font-display">Amount</th>
                  <th className="text-left p-3 font-display">Mode</th>
                  <th className="text-left p-3 font-display">Status</th>
                  <th className="text-left p-3 font-display">Payment</th>
                  <th className="p-3"></th>
                </tr>
              </thead>
              <tbody>
                {links.map((l) => (
                  <tr key={l.link_id} className="border-t border-ink/20" data-testid={`pl-row-${l.link_id}`}>
                    <td className="p-3 text-xs text-[#4A4A4A] whitespace-nowrap">{new Date(l.created_at).toLocaleDateString()}</td>
                    <td className="p-3">
                      <div className="font-bold">{l.label}</div>
                      {l.customer_email && <div className="text-xs text-[#4A4A4A] font-mono">{l.customer_email}</div>}
                      {l.notes && <div className="text-xs text-[#4A4A4A] mt-1">{l.notes}</div>}
                    </td>
                    <td className="p-3 text-xs">{l.category}</td>
                    <td className="p-3 text-right font-mono">£{Number(l.amount).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 border-2 border-ink rounded-md text-xs font-bold uppercase ${l.mode === "live" ? "bg-mint" : "bg-butter"}`}>{l.mode}</span>
                    </td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 border-2 border-ink rounded-md text-xs font-bold uppercase ${l.status === "active" ? "bg-mint" : "bg-peach"}`}>{l.status || "active"}</span>
                    </td>
                    <td className="p-3 text-xs">
                      {l.payment_status || "—"}
                    </td>
                    <td className="p-3 whitespace-nowrap">
                      <button onClick={() => copyLink(l.url)} data-testid={`pl-copy-${l.link_id}`}
                        className="text-xs underline mr-3 inline-flex items-center gap-1">
                        <Copy size={12} weight="bold" /> Copy
                      </button>
                      {l.status !== "archived" && (
                        <button onClick={() => archive(l.link_id)} data-testid={`pl-archive-${l.link_id}`}
                          className="text-xs underline inline-flex items-center gap-1">
                          <Archive size={12} weight="bold" /> Archive
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

// ---------------- DPA acceptances log ----------------

function DpaAcceptancesPanel() {
  const [rows, setRows] = useState([]);
  const [reminders, setReminders] = useState(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [a, r] = await Promise.all([
          api.get("/owner/dpa/acceptances"),
          api.get("/owner/dpa/reminders"),
        ]);
        setRows(a.data.acceptances || []);
        setReminders(r.data);
      } catch (e) {
        toast.error(e?.response?.data?.detail || "Could not load acceptances");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const filtered = q
    ? rows.filter((r) =>
        [r.email, r.school_name, r.doc_version, r.kind]
          .filter(Boolean).join(" ").toLowerCase().includes(q.toLowerCase())
      )
    : rows;

  const downloadCsv = async () => {
    try {
      const res = await api.get("/owner/dpa/acceptances.csv", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "text/csv" }));
      const a = document.createElement("a");
      const cd = res.headers["content-disposition"] || "";
      const m = cd.match(/filename="?([^"]+)"?/);
      a.href = url;
      a.download = m?.[1] || "learnify-dpa-acceptances.csv";
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast.error("Export failed");
    }
  };

  return (
    <div className="space-y-4" data-testid="dpa-panel">
      {reminders && (reminders.counts.upcoming + reminders.counts.stale + reminders.counts.never > 0) && (
        <section className="brutal-card p-5 bg-peach" data-testid="dpa-reminders">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <div className="text-xs uppercase tracking-[0.2em] font-bold">Renewal reminders</div>
              <h3 className="font-display font-bold text-lg">
                {reminders.counts.upcoming} due in 30 days · {reminders.counts.stale} on outdated DPA · {reminders.counts.never} never signed
              </h3>
              <p className="text-xs text-[#333] mt-1">Current DPA version: <b>{reminders.current_version}</b></p>
            </div>
          </div>
          <div className="mt-3 space-y-2 max-h-64 overflow-y-auto">
            {reminders.upcoming.map((u) => (
              <div key={"u-" + u.user_id} className="flex flex-wrap items-center gap-2 text-xs bg-white border-2 border-ink rounded-md p-2" data-testid={`reminder-upcoming-${u.user_id}`}>
                <span className="font-mono">{u.email}</span>
                <span className="text-[#4A4A4A]">·</span>
                <span>{u.role}</span>
                <span className="ml-auto font-bold">Renews in {u.days_until_renewal}d · {u.renewal_date}</span>
                <a href={`mailto:${u.email}?subject=Re-accept%20Learnify%20Privacy%20Policy%20%26%20DPA&body=Hi%20${encodeURIComponent(u.name || "")}%2C%0A%0AOur%20Privacy%20Policy%20and%20Data%20Processing%20Agreement%20is%20due%20for%20renewal%20on%20${u.renewal_date}.%20Please%20sign%20in%20to%20Learnify%20and%20re-accept%20the%20latest%20version%20so%20your%20audit%20trail%20stays%20current.%0A%0AThanks.`}
                  className="brutal-btn bg-ink text-white text-xs">Email</a>
              </div>
            ))}
            {reminders.stale.map((u) => (
              <div key={"s-" + u.user_id} className="flex flex-wrap items-center gap-2 text-xs bg-white border-2 border-ink rounded-md p-2" data-testid={`reminder-stale-${u.user_id}`}>
                <span className="font-mono">{u.email}</span>
                <span className="text-[#4A4A4A]">·</span>
                <span>{u.role}</span>
                <span className="ml-auto font-bold">On v{u.dpa_accepted_version} — needs v{u.current_version}</span>
                <a href={`mailto:${u.email}?subject=Please%20re-accept%20updated%20Privacy%20Policy%20%26%20DPA&body=Hi%20${encodeURIComponent(u.name || "")}%2C%0A%0AWe%27ve%20published%20version%20${u.current_version}%20of%20our%20Privacy%20Policy%20and%20DPA.%20Please%20sign%20in%20to%20Learnify%20and%20accept%20the%20new%20version.`}
                  className="brutal-btn bg-ink text-white text-xs">Email</a>
              </div>
            ))}
            {reminders.never_accepted.map((u) => (
              <div key={"n-" + u.user_id} className="flex flex-wrap items-center gap-2 text-xs bg-white border-2 border-ink rounded-md p-2" data-testid={`reminder-never-${u.user_id}`}>
                <span className="font-mono">{u.email}</span>
                <span className="text-[#4A4A4A]">·</span>
                <span>{u.role}</span>
                <span className="ml-auto font-bold text-red-800">Never signed</span>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Filter by email, school, version…"
          className="brutal-input flex-1 min-w-[220px]"
          data-testid="dpa-filter"
        />
        <button onClick={downloadCsv}
          className="brutal-btn bg-mint hover:bg-white inline-flex items-center gap-2"
          data-testid="dpa-export-csv">
          <DownloadSimple size={16} weight="bold" /> Export CSV
        </button>
      </div>

      {loading ? (
        <div className="brutal-card p-6 text-[#4A4A4A]">Loading…</div>
      ) : (
        <div className="overflow-x-auto brutal-card">
          <table className="min-w-full text-sm">
            <thead className="bg-lavender border-b-2 border-ink">
              <tr>
                <th className="text-left p-3 font-display">When</th>
                <th className="text-left p-3 font-display">Email</th>
                <th className="text-left p-3 font-display">School</th>
                <th className="text-left p-3 font-display">Version</th>
                <th className="text-left p-3 font-display">Kind</th>
                <th className="text-left p-3 font-display">Signature</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr key={r.acceptance_id} className="border-t border-ink/20" data-testid={`dpa-row-${r.acceptance_id}`}>
                  <td className="p-3 text-xs text-[#4A4A4A] whitespace-nowrap">{new Date(r.accepted_at).toLocaleString()}</td>
                  <td className="p-3 font-mono text-xs">{r.email}</td>
                  <td className="p-3">{r.school_name || "—"}</td>
                  <td className="p-3">{r.doc_version || "—"}</td>
                  <td className="p-3">
                    <span className={`px-2 py-0.5 border-2 border-ink rounded-md text-xs font-bold ${r.kind === "signed_pdf_download" ? "bg-butter" : "bg-mint"}`}>
                      {r.kind || "accept"}
                    </span>
                  </td>
                  <td className="p-3 font-mono text-xs break-all">{(r.signature_sha256 || "").slice(0, 16)}…</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={6} className="p-6 text-center text-[#4A4A4A]">No acceptances match.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
