import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { ShieldWarning, X } from "@phosphor-icons/react";

const STAFF_ROLES = new Set(["owner", "school_admin", "teacher"]);
const DISMISS_KEY = "learnify_mfa_nudge_dismissed_until";
const REMIND_HOURS = 24;

export default function MfaNudgeBanner() {
  const { user } = useAuth();
  const [enabled, setEnabled] = useState(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (!user || !STAFF_ROLES.has(user.role)) return;
    try {
      const until = Number(localStorage.getItem(DISMISS_KEY) || 0);
      if (until && Date.now() < until) { setDismissed(true); return; }
    } catch {}
    let alive = true;
    api.get("/auth/mfa/status")
      .then(({ data }) => { if (alive) setEnabled(!!data.enabled); })
      .catch(() => { if (alive) setEnabled(null); });
    return () => { alive = false; };
  }, [user]);

  if (!user || !STAFF_ROLES.has(user.role)) return null;
  if (enabled !== false) return null;
  if (dismissed) return null;

  const dismiss = () => {
    try { localStorage.setItem(DISMISS_KEY, String(Date.now() + REMIND_HOURS * 3600 * 1000)); } catch {}
    setDismissed(true);
  };

  return (
    <div className="bg-butter border-b-2 border-ink px-4 py-2.5 flex flex-wrap items-center gap-3 justify-center text-sm" data-testid="mfa-nudge-banner">
      <ShieldWarning size={18} weight="fill" />
      <span>
        <b>Turn on two-factor auth</b> — staff accounts should be protected with a 6-digit authenticator code.
      </span>
      <Link to="/mfa" data-testid="mfa-nudge-cta"
        className="brutal-btn bg-ink text-white text-xs inline-flex items-center gap-1">
        Set up MFA
      </Link>
      <button onClick={dismiss} data-testid="mfa-nudge-dismiss"
        aria-label="Remind me later"
        className="text-[#4A4A4A] hover:text-ink inline-flex items-center gap-1 text-xs">
        <X size={14} weight="bold" /> Remind me later
      </button>
    </div>
  );
}
