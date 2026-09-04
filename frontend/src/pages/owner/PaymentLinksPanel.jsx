import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Link as LinkIcon, Copy, Archive, EnvelopeSimple, ArrowsClockwise } from "@phosphor-icons/react";

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

const gbp = (n) => `£${Number(n).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function monthKey(iso) {
  try { const d = new Date(iso); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`; } catch { return "unknown"; }
}

function buildQuoteMailto(link) {
  const to = link.customer_email || "";
  const subject = `Learnify · ${link.label} — payment link (${gbp(link.amount)})`;
  const body =
`Hi,

Thanks for chatting about Learnify. Here's the secure Stripe payment link for the licence we discussed:

• ${link.label}
• Amount: ${gbp(link.amount)} GBP
• Category: ${link.category}
• Link: ${link.url}

The link processes in GBP through Stripe Checkout — any card, Apple Pay or Google Pay. Please let us know once it's paid and we'll activate the account.

Any questions, just reply to this email or copy in schoollearnsupport@pm.me.

Best regards,
Learnify · School Learn`;
  const params = new URLSearchParams({ subject, body, cc: "schoollearnsupport@pm.me" });
  return `mailto:${encodeURIComponent(to)}?${params.toString().replace(/\+/g, "%20")}`;
}

export default function PaymentLinksPanel() {
  const [links, setLinks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [stripe, setStripe] = useState(null);
  const [statusFilter, setStatusFilter] = useState("all"); // all | active | archived | paid | unpaid
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

  const copyLink = async (url) => {
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

  const refreshFromStripe = async () => {
    setRefreshing(true);
    try {
      const { data } = await api.post("/owner/billing/payment-links/refresh");
      toast.success(`Refreshed ${data.checked} link${data.checked === 1 ? "" : "s"} · ${data.newly_paid} newly paid`);
      load();
    } catch (ex) {
      toast.error(ex?.response?.data?.detail || "Could not refresh from Stripe");
    } finally {
      setRefreshing(false);
    }
  };

  const filtered = useMemo(() => {
    if (statusFilter === "all") return links;
    if (statusFilter === "active") return links.filter((l) => (l.status || "active") === "active");
    if (statusFilter === "archived") return links.filter((l) => l.status === "archived");
    if (statusFilter === "paid") return links.filter((l) => l.payment_status === "paid");
    if (statusFilter === "unpaid") return links.filter((l) => l.payment_status !== "paid");
    return links;
  }, [links, statusFilter]);

  const summary = useMemo(() => {
    const paid = links.filter((l) => l.payment_status === "paid");
    const total = paid.reduce((sum, l) => sum + Number(l.amount || 0), 0);
    const byMonth = {};
    for (const l of paid) {
      const k = monthKey(l.created_at);
      byMonth[k] = (byMonth[k] || 0) + Number(l.amount || 0);
    }
    const months = Object.entries(byMonth).sort(([a], [b]) => (a < b ? 1 : -1)).slice(0, 6);
    return {
      count_active: links.filter((l) => (l.status || "active") === "active").length,
      count_archived: links.filter((l) => l.status === "archived").length,
      count_paid: paid.length,
      count_pending: links.filter((l) => l.payment_status !== "paid").length,
      total_gbp: total,
      months,
    };
  }, [links]);

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
            <button onClick={refreshFromStripe} disabled={refreshing} data-testid="pl-refresh-stripe"
              className="brutal-btn bg-white inline-flex items-center gap-2 disabled:opacity-60">
              <ArrowsClockwise size={14} weight="bold" /> {refreshing ? "Refreshing…" : "Refresh from Stripe"}
            </button>
          </div>
        </div>
      )}

      <section className="grid gap-3 md:grid-cols-4" data-testid="pl-summary">
        <SummaryCard bg="bg-mint"     label="Paid links"     value={summary.count_paid}    hint={`${gbp(summary.total_gbp)} total`} tid="pl-summary-paid" />
        <SummaryCard bg="bg-butter"   label="Pending"        value={summary.count_pending} hint="Not yet paid" tid="pl-summary-pending" />
        <SummaryCard bg="bg-lavender" label="Active links"   value={summary.count_active}  hint={`${summary.count_archived} archived`} tid="pl-summary-active" />
        <SummaryCard bg="bg-white"    label="This month"     value={summary.months[0] ? gbp(summary.months[0][1]) : gbp(0)}
                     hint={summary.months[0] ? summary.months[0][0] : "—"} tid="pl-summary-month" />
      </section>

      {summary.months.length >= 1 && (
        <section className="brutal-card p-5 bg-white" data-testid="pl-monthly-totals">
          <div className="text-xs uppercase tracking-[0.2em] font-bold mb-3 text-[#4A4A4A]">Paid revenue by month (GBP)</div>
          <div className="space-y-2">
            {summary.months.map(([m, v]) => {
              const max = summary.months[0][1] || 1;
              const w = Math.max(4, Math.round((v / max) * 100));
              return (
                <div key={m} className="flex items-center gap-3 text-sm">
                  <div className="w-20 font-mono text-xs text-[#4A4A4A]">{m}</div>
                  <div className="flex-1 bg-paper border-2 border-ink rounded-md h-6 overflow-hidden">
                    <div className="h-full bg-mint" style={{ width: `${w}%` }} />
                  </div>
                  <div className="w-28 text-right font-mono font-bold">{gbp(v)}</div>
                </div>
              );
            })}
          </div>
        </section>
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
            {gbp(lastCreated.amount)} · {lastCreated.mode} mode · Session <code className="font-mono text-xs">{lastCreated.session_id?.slice(0, 12)}…</code>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <input readOnly value={lastCreated.url} className="brutal-input flex-1 min-w-[280px] font-mono text-xs" data-testid="pl-last-url" />
            <button onClick={() => copyLink(lastCreated.url)} data-testid="pl-copy-last"
              className="brutal-btn bg-white inline-flex items-center gap-2">
              <Copy size={14} weight="bold" /> Copy
            </button>
            <a href={buildQuoteMailto(lastCreated)} data-testid="pl-email-last"
              className="brutal-btn bg-white inline-flex items-center gap-2">
              <EnvelopeSimple size={14} weight="bold" /> Email
            </a>
            <a href={lastCreated.url} target="_blank" rel="noreferrer" className="brutal-btn bg-ink text-white">Open</a>
          </div>
        </section>
      )}

      <section>
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <h2 className="font-display font-extrabold text-2xl tracking-tight">Payment links</h2>
          <div className="inline-flex border-2 border-ink rounded-md bg-white shadow-brutal" data-testid="pl-filter">
            {["all", "active", "archived", "paid", "unpaid"].map((k) => (
              <button key={k} onClick={() => setStatusFilter(k)} data-testid={`pl-filter-${k}`}
                className={`px-3 py-1.5 text-xs font-bold uppercase ${statusFilter === k ? "bg-ink text-white" : ""}`}>
                {k}
              </button>
            ))}
          </div>
        </div>
        {loading ? (
          <div className="brutal-card p-6 text-[#4A4A4A]">Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="brutal-card p-6 text-[#4A4A4A]">
            {links.length === 0 ? "No links minted yet. Use the form above to create your first bespoke Stripe checkout URL." : "No links match this filter."}
          </div>
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
                {filtered.map((l) => (
                  <tr key={l.link_id} className="border-t border-ink/20" data-testid={`pl-row-${l.link_id}`}>
                    <td className="p-3 text-xs text-[#4A4A4A] whitespace-nowrap">{new Date(l.created_at).toLocaleDateString()}</td>
                    <td className="p-3">
                      <div className="font-bold">{l.label}</div>
                      {l.customer_email && <div className="text-xs text-[#4A4A4A] font-mono">{l.customer_email}</div>}
                      {l.notes && <div className="text-xs text-[#4A4A4A] mt-1">{l.notes}</div>}
                    </td>
                    <td className="p-3 text-xs">{l.category}</td>
                    <td className="p-3 text-right font-mono">{gbp(l.amount)}</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 border-2 border-ink rounded-md text-xs font-bold uppercase ${l.mode === "live" ? "bg-mint" : "bg-butter"}`}>{l.mode}</span>
                    </td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 border-2 border-ink rounded-md text-xs font-bold uppercase ${l.status === "archived" ? "bg-peach" : "bg-mint"}`}>{l.status || "active"}</span>
                    </td>
                    <td className="p-3 text-xs">
                      <span className={`px-2 py-0.5 border-2 border-ink rounded-md text-xs font-bold uppercase ${l.payment_status === "paid" ? "bg-mint" : "bg-white"}`}>
                        {l.payment_status || "—"}
                      </span>
                    </td>
                    <td className="p-3 whitespace-nowrap">
                      <button onClick={() => copyLink(l.url)} data-testid={`pl-copy-${l.link_id}`}
                        className="text-xs underline mr-3 inline-flex items-center gap-1">
                        <Copy size={12} weight="bold" /> Copy
                      </button>
                      <a href={buildQuoteMailto(l)} data-testid={`pl-email-${l.link_id}`}
                        className="text-xs underline mr-3 inline-flex items-center gap-1">
                        <EnvelopeSimple size={12} weight="bold" /> Email
                      </a>
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

function SummaryCard({ bg, label, value, hint, tid }) {
  return (
    <div className={`brutal-card p-4 ${bg}`} data-testid={tid}>
      <div className="text-xs tracking-[0.2em] uppercase font-bold text-[#4A4A4A]">{label}</div>
      <div className="font-display font-black text-2xl mt-1">{value}</div>
      <div className="text-xs text-[#4A4A4A] mt-1">{hint}</div>
    </div>
  );
}
