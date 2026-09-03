import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { displayHandle } from "@/lib/displayName";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { ChalkboardTeacher, Users, GraduationCap, X, ArrowRight, CheckCircle } from "@phosphor-icons/react";

const STEPS = [
  {
    icon: ChalkboardTeacher,
    title: "1 · Invite your teachers",
    body: "Add colleagues by email. They'll get access to lesson planning, homework, and the register.",
    ctaLabel: "Add teachers now",
    ctaTo: "/classes",
    bg: "bg-mint",
  },
  {
    icon: GraduationCap,
    title: "2 · Set up your classes",
    body: "Create or edit form groups (7A, 8B, etc.) and assign a subject or year group.",
    ctaLabel: "Manage classes",
    ctaTo: "/classes",
    bg: "bg-butter",
  },
  {
    icon: Users,
    title: "3 · Invite your students",
    body: "Paste student emails into each class. They'll be able to sign in and access homework straight away.",
    ctaLabel: "Add students",
    ctaTo: "/classes",
    bg: "bg-lavender",
  },
];

export default function OnboardingTour() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [state, setState] = useState({ open: false, step: 0 });

  useEffect(() => {
    if (!user) return;
    // Only show for school admins on their first ever login.
    if (user.role !== "school_admin") return;
    api.get("/onboarding/state").then(({ data }) => {
      const s = data.onboarding || {};
      if (!s.completed && !s.dismissed) {
        setState({ open: true, step: s.step || 0 });
      }
    }).catch(() => {});
  }, [user]);

  const patch = (payload) => api.patch("/onboarding/state", payload).catch(() => {});

  const next = () => {
    if (state.step >= STEPS.length - 1) {
      patch({ completed: true });
      setState({ open: false, step: state.step });
      return;
    }
    const s = state.step + 1;
    patch({ step: s });
    setState({ open: true, step: s });
  };

  const dismiss = () => {
    patch({ dismissed: true });
    setState({ open: false, step: state.step });
  };

  const jumpToCta = () => {
    const s = STEPS[state.step];
    if (state.step >= STEPS.length - 1) {
      patch({ completed: true });
    } else {
      patch({ step: state.step + 1 });
    }
    setState({ open: false, step: state.step });
    navigate(s.ctaTo);
  };

  if (!state.open) return null;
  const step = STEPS[state.step];
  const Icon = step.icon;

  return (
    <div className="fixed inset-0 z-[9998] bg-ink/60 backdrop-blur-sm flex items-center justify-center p-4" data-testid="onboarding-tour">
      <div className={`bg-paper border-2 border-ink brutal-shadow w-full max-w-lg rounded-lg overflow-hidden`}>
        <div className={`${step.bg} border-b-2 border-ink p-6`}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] font-bold">
              <span>Welcome, {user ? displayHandle(user) : "Admin"}</span>
              <span>·</span>
              <span data-testid="onboarding-step-indicator">Step {state.step + 1} of {STEPS.length}</span>
            </div>
            <button onClick={dismiss} aria-label="Close" data-testid="onboarding-dismiss" className="text-ink hover:text-red-800">
              <X size={18} weight="bold" />
            </button>
          </div>
          <div className="flex items-start gap-4">
            <div className="border-2 border-ink rounded-md bg-white p-3">
              <Icon size={28} weight="duotone" />
            </div>
            <div>
              <h2 className="font-display font-black text-2xl">{step.title}</h2>
              <p className="text-sm mt-2">{step.body}</p>
            </div>
          </div>
        </div>
        <div className="p-6 flex flex-wrap gap-3 items-center justify-between">
          <div className="flex gap-1">
            {STEPS.map((_, i) => (
              <span key={i} className={`h-1.5 rounded-full transition-all ${i === state.step ? "w-8 bg-ink" : "w-3 bg-ink/30"}`} />
            ))}
          </div>
          <div className="flex gap-2">
            <button onClick={dismiss} className="brutal-btn bg-white text-sm" data-testid="onboarding-skip">
              Skip for now
            </button>
            <button onClick={jumpToCta} className="brutal-btn bg-mint hover:bg-white text-sm inline-flex items-center gap-1" data-testid="onboarding-cta">
              {step.ctaLabel} <ArrowRight size={14} weight="bold" />
            </button>
            {state.step < STEPS.length - 1 ? (
              <button onClick={next} className="brutal-btn bg-ink text-white text-sm inline-flex items-center gap-1" data-testid="onboarding-next">
                Next <ArrowRight size={14} weight="bold" />
              </button>
            ) : (
              <button onClick={next} className="brutal-btn bg-ink text-white text-sm inline-flex items-center gap-1" data-testid="onboarding-finish">
                <CheckCircle size={14} weight="bold" /> All done
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
