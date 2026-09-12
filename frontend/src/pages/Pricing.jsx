import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AppLayout from "@/components/AppLayout";
import GlobalNav from "@/components/GlobalNav";
import { api } from "@/lib/api";
import { CheckCircle, Sparkle, Crown, Buildings, XCircle, ArrowsClockwise, Prohibit, EnvelopeSimple, ArrowDown, ArrowCounterClockwise } from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

const FEATURES = {
  free:          ["5 AI generations per day", "Browse all subjects", "Homework help", { neg: true, text: "No practice papers" }],
  basic:         ["50 AI generations per day", "All subjects", "Homework help", "Basic progress tracking"],
  standard:      ["Everything in Basic", "AI-generated mock papers", "Exam-board picker", "Extended progress reports"],
  pro:           ["Everything in Standard", "Unlimited generations", "All exam boards", "Priority support"],
  school_small:  ["Everything in Pro for every student", "Under 500 student licence", "Teacher panel + lesson planner", "AI homework analysis", "Detentions, attendance, achievements", "Invoice billing available"],
  school_medium: ["Everything in Pro for every student", "500–1,000 student licence", "Teacher panel + lesson planner", "AI homework analysis", "Detentions, attendance, achievements", "Invoice billing + onboarding"],
  school_large:  ["Everything in Pro for every student", "1,000+ student licence", "Teacher panel + lesson planner", "AI homework analysis", "Detentions, attendance, achievements", "Dedicated success manager"],
  mat_1_5:       ["Everything in School plans", "3–5 schools licenced", "Central MAT dashboard", "Consolidated billing", "SLA support"],
  mat_10_30:     ["Everything in Small MAT", "10+ schools", "Trust-wide analytics", "Named account manager", "Priority engineering support"],
};

const ICONS = { free: Sparkle, basic: Sparkle, standard: Sparkle, pro: Crown, school_small: Buildings, school_medium: Buildings, school_large: Buildings, mat_1_5: Buildings, mat_10_30: Buildings };
const ACCENTS = { free: "bg-white", basic: "bg-mint", standard: "bg-butter", pro: "bg-lavender", school_small: "bg-peach", school_medium: "bg-peach", school_large: "bg-peach", mat_1_5: "bg-mint", mat_10_30: "bg-mint" };

export default function Pricing() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [plans, setPlans] = useState([]);
  const [billing, setBilling] = useState(null);
  const [loading, setLoading] = useState(null);
  const [cancelBusy, setCancelBusy] = useState(false);
  const [downgradeBusy, setDowngradeBusy] = useState(null);

  const refreshBilling = async () => {
    try {
      const { data: b } = await api.get("/billing/me");
      setBilling(b);
    } catch {}
  };

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/plans");
        setPlans(data.plans || []);
        if (user) {
          await refreshBilling();
        }
      } catch {}
    })();
  }, [user]);

  const subscribe = async (plan_id) => {
    if (!user) { navigate("/login"); return; }
    setLoading(plan_id);
    try {
      const { data } = await api.post("/billing/checkout", { plan_id, origin_url: window.location.origin });
      window.location.href = data.url;
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to start checkout");
    } finally {
      setLoading(null);
    }
  };

  const cancelSubscription = async () => {
    if (!window.confirm(`Cancel your ${billing?.plan?.name} subscription?\n\nYou'll keep full access until ${billing?.expires_at ? new Date(billing.expires_at).toLocaleDateString() : "your period ends"}, then drop to the free plan. You can resume any time before then.`)) return;
    setCancelBusy(true);
    try {
      await api.post("/billing/cancel");
      toast.success("Subscription cancelled. You keep access until it expires.");
      await refreshBilling();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't cancel subscription");
    } finally {
      setCancelBusy(false);
    }
  };

  const PLAN_ORDER = ["free", "basic", "standard", "pro"];
  const PLAN_NAMES = { free: "Free", basic: "Basic", standard: "Standard", pro: "Pro" };

  const scheduleDowngrade = async (new_plan_id) => {
    const name = PLAN_NAMES[new_plan_id];
    const when = billing?.expires_at ? new Date(billing.expires_at).toLocaleDateString() : "your period ends";
    if (!window.confirm(`Switch to ${name} when your current ${billing?.plan?.name} period ends?\n\nYou'll keep full ${billing?.plan?.name} access until ${when}. On that date you'll drop to ${name} and be billed the new price going forward. You can undo any time before then.`)) return;
    setDowngradeBusy(new_plan_id);
    try {
      await api.post("/billing/schedule-downgrade", { new_plan_id });
      toast.success(`Scheduled downgrade to ${name}. Takes effect ${when}.`);
      await refreshBilling();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't schedule downgrade");
    } finally {
      setDowngradeBusy(null);
    }
  };

  const cancelDowngrade = async () => {
    setDowngradeBusy("cancel");
    try {
      await api.post("/billing/cancel-downgrade");
      toast.success("Scheduled change cancelled — you'll stay on your current plan.");
      await refreshBilling();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't cancel scheduled change");
    } finally {
      setDowngradeBusy(null);
    }
  };

  const resumeSubscription = async () => {
    setCancelBusy(true);
    try {
      await api.post("/billing/resume");
      toast.success("Subscription resumed.");
      await refreshBilling();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't resume subscription");
    } finally {
      setCancelBusy(false);
    }
  };

  const individualIds = ["free", "basic", "standard", "pro"];
  const cards = individualIds.map((id) => plans.find((p) => p.id === id)).filter(Boolean);

  const inner = (
    <div className="max-w-6xl mx-auto space-y-10">
      <div className="text-center max-w-2xl mx-auto">
        <div className="text-xs tracking-[0.2em] uppercase font-bold mb-3 text-[#4A4A4A]">Pricing</div>
        <h1 className="font-display font-black text-5xl sm:text-6xl tracking-tight">Pick your plan.</h1>
        <p className="text-[#4A4A4A] mt-4">Cancel anytime. Schools pay annually for the whole school.</p>
        {billing && (
          <div className="mt-6 inline-block brutal-card px-4 py-2 bg-butter text-sm" data-testid="billing-current">
            <span className="font-bold">Current plan:</span>{" "}
            <span className="font-display font-bold uppercase">{billing.plan?.name}</span>
            {billing.expires_at && billing.tier !== "free" && (
              <span className="text-[#4A4A4A] ml-2">
                · {billing.cancel_at_period_end ? "ends" : "expires"} {new Date(billing.expires_at).toLocaleDateString()}
              </span>
            )}
            {billing.lifetime && <span className="ml-2 font-bold uppercase text-[10px] bg-mint border-2 border-ink rounded px-1.5 py-0.5">Lifetime</span>}
          </div>
        )}
      </div>

      {user && billing && billing.tier !== "free" && !billing.lifetime && (
        <div className="brutal-card p-5 bg-white flex flex-wrap items-center justify-between gap-4" data-testid="manage-subscription">
          <div>
            <div className="text-xs uppercase tracking-[0.2em] font-bold mb-1 text-[#4A4A4A]">Manage subscription</div>
            <div className="font-display font-bold text-xl">
              {billing.plan?.name}
              <span className="ml-2 text-[#4A4A4A] font-mono text-sm">
                £{Number(billing.plan?.amount ?? 0).toLocaleString("en-GB")}/{billing.plan?.period}
              </span>
            </div>
            {billing.cancel_at_period_end ? (
              <div className="text-sm mt-1 text-[#8A3B00] font-bold" data-testid="cancel-status">
                Cancelled · you keep access until {billing.expires_at ? new Date(billing.expires_at).toLocaleDateString() : "the period ends"}.
              </div>
            ) : billing.next_tier ? (
              <div className="text-sm mt-1 text-[#8A3B00] font-bold" data-testid="downgrade-status">
                Switching to <span className="uppercase">{PLAN_NAMES[billing.next_tier] || billing.next_tier}</span>
                {billing.expires_at ? ` on ${new Date(billing.expires_at).toLocaleDateString()}` : " at period end"}.
              </div>
            ) : billing.expires_at ? (
              <div className="text-sm mt-1 text-[#4A4A4A]" data-testid="renews-hint">
                Runs until {new Date(billing.expires_at).toLocaleDateString()}. Cancel or switch plans any time — you keep access until then.
              </div>
            ) : null}
          </div>
          <div className="flex gap-2 flex-wrap">
            {billing.cancel_at_period_end ? (
              <button
                onClick={resumeSubscription}
                disabled={cancelBusy}
                data-testid="resume-subscription-btn"
                className="brutal-btn bg-ink text-white inline-flex items-center gap-2 disabled:opacity-60"
              >
                <ArrowsClockwise size={14} weight="bold" /> {cancelBusy ? "Resuming…" : "Resume subscription"}
              </button>
            ) : billing.next_tier ? (
              <button
                onClick={cancelDowngrade}
                disabled={downgradeBusy === "cancel"}
                data-testid="cancel-downgrade-btn"
                className="brutal-btn bg-ink text-white inline-flex items-center gap-2 disabled:opacity-60"
              >
                <ArrowCounterClockwise size={14} weight="bold" /> {downgradeBusy === "cancel" ? "Undoing…" : "Undo scheduled change"}
              </button>
            ) : (
              <>
                {PLAN_ORDER.slice(0, PLAN_ORDER.indexOf(billing.tier)).filter((t) => t !== "free").map((t) => (
                  <button
                    key={t}
                    onClick={() => scheduleDowngrade(t)}
                    disabled={!!downgradeBusy}
                    data-testid={`downgrade-to-${t}-btn`}
                    className="brutal-btn bg-butter hover:bg-white inline-flex items-center gap-2 disabled:opacity-60"
                  >
                    <ArrowDown size={14} weight="bold" /> {downgradeBusy === t ? "Scheduling…" : `Downgrade to ${PLAN_NAMES[t]}`}
                  </button>
                ))}
                <button
                  onClick={cancelSubscription}
                  disabled={cancelBusy}
                  data-testid="cancel-subscription-btn"
                  className="brutal-btn bg-white hover:bg-peach inline-flex items-center gap-2 disabled:opacity-60"
                >
                  <Prohibit size={14} weight="bold" /> {cancelBusy ? "Cancelling…" : "Cancel subscription"}
                </button>
              </>
            )}
          </div>
        </div>
      )}

      <div className="flex justify-center">
        <div className="border-2 border-ink rounded-md p-1 bg-white inline-flex shadow-brutal">
          <button data-testid="pricing-tab-individual" className="px-4 py-2 rounded font-bold text-sm bg-ink text-white">Individuals</button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-4 md:grid-cols-2">
        {cards.map((p) => {
          const Icon = ICONS[p.id] || Sparkle;
          const isCurrent = billing?.tier === p.id;
          const isFree = p.amount === 0;
          return (
            <div key={p.id} className={`brutal-card p-6 flex flex-col ${ACCENTS[p.id]}`} data-testid={`plan-card-${p.id}`}>
              <div className="flex items-center gap-2 mb-3">
                <div className="border-2 border-ink bg-white rounded-md p-2 shadow-brutal"><Icon size={20} weight="duotone" /></div>
                <div className="font-display font-bold text-xl">{p.name}</div>
              </div>
              <div className="mb-1">
                <span className="font-display font-black text-4xl">£{Number(p.amount).toLocaleString("en-GB")}</span>
                <span className="text-sm text-[#4A4A4A] ml-1">/{p.period}</span>
              </div>
              <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A] mb-4">
                {p.id.startsWith("mat") ? "Per MAT, whole-trust licence" : p.id.startsWith("school") ? "Per school, whole-school licence" : "Per student"}
              </div>
              <ul className="space-y-2 text-sm mb-6 grow">
                {(FEATURES[p.id] || []).map((f, i) => {
                  const neg = typeof f === "object" && f.neg;
                  const text = typeof f === "string" ? f : f.text;
                  return (
                    <li key={i} className="flex items-start gap-2">
                      {neg ? <XCircle size={16} weight="bold" className="mt-0.5 text-[#4A4A4A] shrink-0" />
                           : <CheckCircle size={16} weight="fill" className="mt-0.5 shrink-0" />}
                      <span className={neg ? "text-[#4A4A4A]" : ""}>{text}</span>
                    </li>
                  );
                })}
              </ul>
              {isCurrent ? (
                <button disabled className="brutal-btn bg-white opacity-80" data-testid={`plan-current-${p.id}`}>Current plan</button>
              ) : isFree ? (
                <Link to={user ? "/dashboard" : "/register"} className="brutal-btn bg-white hover:bg-butter text-center" data-testid={`plan-cta-${p.id}`}>
                  {user ? "Go to dashboard" : "Get started"}
                </Link>
              ) : p.id.startsWith("school") ? (
                <Link to="/signup/school" className="brutal-btn bg-ink text-white text-center" data-testid={`plan-cta-${p.id}`}>
                  Register your school
                </Link>
              ) : p.id.startsWith("mat") ? (
                <Link to="/contact" className="brutal-btn bg-ink text-white text-center" data-testid={`plan-cta-${p.id}`}>
                  Contact sales
                </Link>
              ) : (
                <button onClick={() => subscribe(p.id)} disabled={loading === p.id}
                  data-testid={`plan-cta-${p.id}`}
                  className="brutal-btn bg-ink text-white hover:bg-[#2A2A2A] disabled:opacity-60">
                  {loading === p.id ? "Redirecting…" : "Subscribe"}
                </button>
              )}
            </div>
          );
        })}
      </div>

      <p className="text-xs text-[#4A4A4A] text-center max-w-2xl mx-auto">
        Prices in GBP (£). Individual plans billed monthly · cancel anytime.
      </p>

      <div className="brutal-card p-6 bg-lavender max-w-3xl mx-auto" data-testid="pricing-schools-contact">
        <div className="flex items-start gap-3">
          <div className="border-2 border-ink bg-white rounded-md p-2 shadow-brutal shrink-0">
            <Buildings size={22} weight="duotone" />
          </div>
          <div className="grow">
            <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#4A4A4A]">Schools · MATs · Districts</div>
            <div className="font-display font-bold text-xl mt-1">Whole-school & multi-academy trust licences</div>
            <p className="text-sm text-[#333] mt-2">
              Every school and MAT gets a bespoke annual quote — pupil count, MAT-wide dashboards,
              procurement paperwork, invoicing terms, onboarding. Contact us for pricing and a demo.
            </p>
            <a href="mailto:schoollearnsupport@pm.me?subject=Learnify%20school%20%2F%20MAT%20enquiry&body=Hi%20Learnify%20team%2C%0A%0AWe%27d%20like%20to%20discuss%20a%20whole-school%20or%20MAT%20licence.%0A%0A-%20Organisation%20name%3A%20%0A-%20Number%20of%20schools%2Fpupils%3A%20%0A-%20Preferred%20start%20date%3A%20%0A-%20Anything%20else%20we%20should%20know%3A%20%0A%0AThanks."
               className="brutal-btn bg-ink text-white inline-flex items-center gap-2 mt-4"
               data-testid="pricing-schools-contact-btn">
              <EnvelopeSimple size={16} weight="bold" /> Contact us for schools pricing
            </a>
          </div>
        </div>
      </div>

      <div className="brutal-card p-5 bg-butter text-center max-w-3xl mx-auto" data-testid="pricing-custom-plan-banner">
        <div className="text-xs uppercase tracking-[0.2em] font-bold mb-1 text-[#4A4A4A]">Need something different?</div>
        <div className="font-display font-bold text-lg">
          Talk to us about a bespoke plan — email{" "}
          <a href="mailto:schoollearnsupport@pm.me?subject=Custom%20Learnify%20plan%20enquiry&body=Hi%20Learnify%20team%2C%0A%0AWe%27d%20like%20a%20custom%20plan.%20A%20few%20things%20about%20us%3A%0A%0A-%20Organisation%20name%3A%20%0A-%20Number%20of%20schools%2Fpupils%3A%20%0A-%20What%20you%20need%20that%20our%20listed%20plans%20don%27t%20cover%3A%20%0A-%20Timeline%3A%20%0A%0AThanks."
             className="underline font-mono"
             data-testid="pricing-support-email">
            schoollearnsupport@pm.me
          </a>
        </div>
        <p className="text-sm text-[#4A4A4A] mt-2">
          Tell us who you are, why you want a custom plan, and roughly how many pupils or schools — we'll come back within one working day.
        </p>
      </div>
    </div>
  );

  return user ? <AppLayout>{inner}</AppLayout> : (
    <div className="min-h-screen bg-paper">
      <GlobalNav />
      <div className="p-6 py-12">{inner}</div>
    </div>
  );
}
