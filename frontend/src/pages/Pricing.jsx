import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AppLayout from "@/components/AppLayout";
import GlobalNav from "@/components/GlobalNav";
import { api } from "@/lib/api";
import { CheckCircle, Sparkle, Crown, Buildings, XCircle } from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

const FEATURES = {
  free: ["5 AI generations per day", "Browse all subjects", "Focus Mode timer", { neg: true, text: "No practice papers" }],
  basic: ["30 AI generations per day", "All subjects unlocked", "Generic practice papers", "Flashcards & quizzes", "AI tutor chat"],
  standard: ["Unlimited AI generations", "All subjects unlocked", "Full practice papers + PDF", "Unlimited AI tutor", "Priority queue"],
  pro: ["Everything in Standard", "Exam-board papers (AQA, Edexcel, OCR, IB, CIE)", "GCSE / A-Level / IB style", "Priority support"],
  school_small:  ["Everything in Pro for every student", "600–1,000 student licence", "Teacher panel + lesson planner", "AI homework analysis (class + per-student)", "Detentions, attendance, achievements", "Invoice billing available"],
  school_medium: ["Everything in Pro for every student", "750–1,500 student licence", "Teacher panel + lesson planner", "AI homework analysis (class + per-student)", "Detentions, attendance, achievements", "Invoice billing + onboarding"],
  school_large:  ["Everything in Pro for every student", "1,500+ student licence", "Teacher panel + lesson planner", "AI homework analysis (class + per-student)", "Detentions, attendance, achievements", "Dedicated success manager"],
};
const ICONS = { free: Sparkle, basic: Sparkle, standard: Sparkle, pro: Crown, school_small: Buildings, school_medium: Buildings, school_large: Buildings };
const ACCENTS = { free: "bg-white", basic: "bg-mint", standard: "bg-butter", pro: "bg-lavender", school_small: "bg-peach", school_medium: "bg-peach", school_large: "bg-peach" };

export default function Pricing() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [plans, setPlans] = useState([]);
  const [billing, setBilling] = useState(null);
  const [loading, setLoading] = useState(null);
  const [tab, setTab] = useState("individual");

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/plans");
        setPlans(data.plans || []);
        if (user) {
          const { data: b } = await api.get("/billing/me");
          setBilling(b);
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

  const individualIds = ["free", "basic", "standard", "pro"];
  const schoolIds = ["school_small", "school_medium", "school_large"];
  const shown = tab === "individual" ? individualIds : schoolIds;
  const cards = shown.map((id) => plans.find((p) => p.id === id)).filter(Boolean);

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
              <span className="text-[#4A4A4A] ml-2">· expires {new Date(billing.expires_at).toLocaleDateString()}</span>
            )}
          </div>
        )}
      </div>

      <div className="flex justify-center">
        <div className="border-2 border-ink rounded-md p-1 bg-white inline-flex shadow-brutal">
          <button onClick={() => setTab("individual")} data-testid="pricing-tab-individual"
            className={`px-4 py-2 rounded font-bold text-sm ${tab === "individual" ? "bg-ink text-white" : ""}`}>Individuals</button>
          <button onClick={() => setTab("school")} data-testid="pricing-tab-school"
            className={`px-4 py-2 rounded font-bold text-sm ${tab === "school" ? "bg-ink text-white" : ""}`}>Schools</button>
        </div>
      </div>

      <div className={`grid gap-4 ${tab === "individual" ? "lg:grid-cols-4 md:grid-cols-2" : "lg:grid-cols-3 md:grid-cols-2"}`}>
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
                {p.id.startsWith("school") ? "Per school, whole-school licence" : "Per student"}
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
        Prices in GBP. School plans are annual whole-school licences. Test mode — no real charges on the demo.
      </p>
    </div>
  );

  return user ? <AppLayout>{inner}</AppLayout> : (
    <div className="min-h-screen bg-paper">
      <GlobalNav />
      <div className="p-6 py-12">{inner}</div>
    </div>
  );
}
