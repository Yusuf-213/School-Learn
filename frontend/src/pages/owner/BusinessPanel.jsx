import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function BusinessPanel() {
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
