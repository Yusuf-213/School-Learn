import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Bank, Crown, ArrowSquareOut, CheckCircle, CurrencyGbp, Receipt, FloppyDisk, Warning } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Payouts() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [form, setForm] = useState({
    bank_account_holder_name: "",
    bank_account_iban: "",
    bank_sort_code: "",
    bank_account_number_last4: "",
    stripe_account_id: "",
    payout_currency: "gbp",
    notes: "",
  });
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      const { data: d } = await api.get("/owner/payouts");
      setData(d);
      setForm({ ...form, ...(d.settings || {}) }); // eslint-disable-line
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to load");
    }
  };
  useEffect(() => { load(); }, []);

  if (user?.role !== "owner") {
    return (
      <AppLayout>
        <div className="brutal-card p-8 max-w-md mx-auto">
          <Crown size={36} weight="duotone" />
          <h1 className="font-display font-black text-2xl mt-3">Payouts</h1>
          <p className="text-[#4A4A4A] mt-2">Only the owner can manage payouts.</p>
        </div>
      </AppLayout>
    );
  }

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.put("/owner/payouts", form);
      toast.success("Payout settings saved.");
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppLayout>
      <div className="max-w-4xl space-y-6" data-testid="payouts-page">
        <div>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A]">Payouts</div>
          <h1 className="font-display font-black text-4xl tracking-tight">Get paid.</h1>
          <p className="text-[#4A4A4A] mt-3 max-w-2xl">
            Money paid into Learnify's Stripe account routes automatically to your linked bank. Final payout configuration (frequency, currency, KYC) is done in your Stripe Dashboard — link below. Save the bank account on file here for your records and admin reference.
          </p>
        </div>

        {data && (
          <div className="grid sm:grid-cols-3 gap-3">
            <Stat label="Total revenue" value={`£${data.revenue.total_gbp.toLocaleString("en-GB", { minimumFractionDigits: 2 })}`} icon={CurrencyGbp} bg="bg-mint" />
            <Stat label="Paid transactions" value={data.revenue.transaction_count} icon={Receipt} bg="bg-butter" />
            <Stat label="Promo schools" value={data.promo_schools?.length || 0} icon={CheckCircle} bg="bg-lavender" />
          </div>
        )}

        <div className="brutal-card p-6 bg-butter">
          <div className="flex items-start gap-3">
            <Warning size={22} weight="duotone" />
            <div className="text-sm">
              <strong>Where payouts actually happen.</strong> Stripe handles the legal money movement. To link your bank account so funds reach you:
              <ol className="list-decimal pl-5 mt-2 space-y-1">
                <li>Open the <a target="_blank" rel="noreferrer" className="underline font-bold" href={data?.stripe_dashboard_url || "https://dashboard.stripe.com/settings/payouts"} data-testid="stripe-dashboard-link">Stripe Dashboard payout settings <ArrowSquareOut size={12} className="inline mb-0.5" /></a>.</li>
                <li>Sign in with the email tied to this Learnify Stripe account.</li>
                <li>Add your UK bank (sort code + account number) and verify identity (KYC).</li>
                <li>Set payout schedule (daily / weekly / monthly).</li>
              </ol>
              Once verified, every successful school subscription on Learnify will land in your bank automatically.
            </div>
          </div>
        </div>

        <form onSubmit={save} className="brutal-card p-6 space-y-4 bg-white">
          <h2 className="font-display font-bold text-2xl flex items-center gap-2"><Bank size={22} weight="duotone" /> Bank account on file</h2>
          <p className="text-xs text-[#4A4A4A]">For your records. We never charge here — this is metadata mirroring what's set in Stripe.</p>
          <div className="grid sm:grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Account holder name</span>
              <input data-testid="payout-holder-name" value={form.bank_account_holder_name || ""} onChange={(e) => setForm({ ...form, bank_account_holder_name: e.target.value })} className="mt-2 brutal-input w-full" placeholder="Yusuf M" />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Currency</span>
              <select data-testid="payout-currency" value={form.payout_currency || "gbp"} onChange={(e) => setForm({ ...form, payout_currency: e.target.value })} className="mt-2 brutal-input w-full bg-white">
                <option value="gbp">GBP (£)</option><option value="eur">EUR (€)</option><option value="usd">USD ($)</option>
              </select>
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Sort code (UK)</span>
              <input data-testid="payout-sort-code" value={form.bank_sort_code || ""} onChange={(e) => setForm({ ...form, bank_sort_code: e.target.value })} className="mt-2 brutal-input w-full font-mono" placeholder="12-34-56" />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Account number — last 4</span>
              <input data-testid="payout-acc-last4" maxLength={4} value={form.bank_account_number_last4 || ""} onChange={(e) => setForm({ ...form, bank_account_number_last4: e.target.value })} className="mt-2 brutal-input w-32 font-mono" placeholder="1234" />
            </label>
            <label className="block sm:col-span-2">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">IBAN (international, optional)</span>
              <input data-testid="payout-iban" value={form.bank_account_iban || ""} onChange={(e) => setForm({ ...form, bank_account_iban: e.target.value })} className="mt-2 brutal-input w-full font-mono uppercase" placeholder="GB29 NWBK 6016 1331 9268 19" />
            </label>
            <label className="block sm:col-span-2">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Stripe Connect account ID (acct_…, optional)</span>
              <input data-testid="payout-stripe-id" value={form.stripe_account_id || ""} onChange={(e) => setForm({ ...form, stripe_account_id: e.target.value })} className="mt-2 brutal-input w-full font-mono" placeholder="acct_1Nxxxxxxxxxxxxxx" />
              <span className="text-xs text-[#4A4A4A] inline-block mt-1">Only needed if you operate multiple Stripe accounts and want a specific one to receive Learnify payouts.</span>
            </label>
            <label className="block sm:col-span-2">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Notes</span>
              <textarea data-testid="payout-notes" rows={2} value={form.notes || ""} onChange={(e) => setForm({ ...form, notes: e.target.value })} className="mt-2 brutal-input w-full" placeholder="e.g. settlement preference, accountant contact" />
            </label>
          </div>
          <button type="submit" disabled={saving} data-testid="payout-save-btn" className="brutal-btn bg-ink text-white inline-flex items-center gap-2 disabled:opacity-60">
            <FloppyDisk size={16} weight="bold" /> {saving ? "Saving…" : "Save settings"}
          </button>
        </form>

        {data?.recent_payments?.length > 0 && (
          <section>
            <h2 className="font-display font-bold text-2xl mb-3">Recent paid transactions</h2>
            <div className="brutal-card overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-butter border-b-2 border-ink"><tr>
                  <th className="text-left p-3 font-display">Plan</th>
                  <th className="text-left p-3 font-display">Email</th>
                  <th className="text-right p-3 font-display">Amount</th>
                  <th className="text-left p-3 font-display">Date</th>
                </tr></thead>
                <tbody>
                  {data.recent_payments.map((p, i) => (
                    <tr key={i} className="border-t border-ink/20" data-testid={`payout-tx-${i}`}>
                      <td className="p-3 font-bold">{p.plan_id}</td>
                      <td className="p-3 text-[#4A4A4A]">{p.email}</td>
                      <td className="p-3 text-right font-mono">£{((p.amount_total || (p.amount || 0) * 100) / 100).toFixed(2)}</td>
                      <td className="p-3 text-xs text-[#4A4A4A]">{new Date(p.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {data?.promo_schools?.length > 0 && (
          <section>
            <h2 className="font-display font-bold text-2xl mb-3">Schools on a promo code (no payment)</h2>
            <div className="space-y-2">
              {data.promo_schools.map((s, i) => (
                <div key={i} className="brutal-card p-3 bg-white flex justify-between" data-testid={`payout-promo-${i}`}>
                  <div>
                    <div className="font-bold">{s.name}</div>
                    <div className="text-xs text-[#4A4A4A]">{s.subscription_tier}</div>
                  </div>
                  <span className="px-2 py-0.5 border-2 border-ink rounded-md bg-mint text-xs font-bold uppercase">{s.promo_code_applied}</span>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </AppLayout>
  );
}

function Stat({ label, value, icon: Icon, bg }) {
  return (
    <div className={`brutal-card p-4 ${bg}`}>
      <div className="flex items-center justify-between mb-2"><Icon size={20} weight="duotone" /></div>
      <div className="font-display font-black text-2xl">{value}</div>
      <div className="text-xs tracking-[0.2em] uppercase font-bold mt-1">{label}</div>
    </div>
  );
}
