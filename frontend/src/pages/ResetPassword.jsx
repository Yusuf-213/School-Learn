import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import GlobalNav from "@/components/GlobalNav";
import { Lock, CheckCircle, Warning } from "@phosphor-icons/react";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") || "";
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setErr("");
    if (pw !== pw2) { setErr("The two passwords don't match."); return; }
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: pw });
      setDone(true);
      setTimeout(() => navigate("/login", { replace: true }), 2500);
    } catch (ex) {
      setErr(ex.response?.data?.detail || "Could not reset password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper">
      <GlobalNav />
      <div className="flex items-center justify-center p-6 py-10">
        <div className="w-full max-w-md">
          <div className="brutal-card p-8" data-testid="reset-password-page">
            <h1 className="font-display font-black text-4xl tracking-tight mb-2">New password.</h1>

            {!token ? (
              <div className="border-2 border-focus bg-peach p-3 rounded-md text-sm" data-testid="reset-no-token">
                This reset link is missing its token. Please request a new link from the{" "}
                <Link to="/forgot-password" className="font-bold underline">forgot password</Link> page.
              </div>
            ) : done ? (
              <div className="space-y-4" data-testid="reset-success">
                <div className="border-2 border-ink bg-mint p-4 rounded-md flex items-start gap-2 text-sm">
                  <CheckCircle size={20} weight="fill" className="mt-0.5 shrink-0" />
                  <span>Password updated. Taking you to sign in…</span>
                </div>
                <Link to="/login" className="brutal-btn bg-ink text-white w-full inline-block text-center">Sign in now</Link>
              </div>
            ) : (
              <>
                <p className="text-[#4A4A4A] mb-6">Choose a strong new password — at least 10 characters with upper & lower case, a number and a symbol.</p>
                {err && (
                  <div className="mb-4 border-2 border-focus bg-peach text-ink p-3 rounded-md flex items-center gap-2 text-sm" data-testid="reset-error">
                    <Warning size={18} weight="bold" /> {err}
                  </div>
                )}
                <form onSubmit={onSubmit} className="space-y-4">
                  <label className="block">
                    <span className="text-xs uppercase tracking-[0.2em] font-bold flex items-center gap-2"><Lock size={14} /> New password</span>
                    <input data-testid="reset-password-input" type="password" required value={pw}
                      onChange={(e) => setPw(e.target.value)} placeholder="••••••••••"
                      className="mt-2 brutal-input w-full" />
                  </label>
                  <label className="block">
                    <span className="text-xs uppercase tracking-[0.2em] font-bold flex items-center gap-2"><Lock size={14} /> Confirm new password</span>
                    <input data-testid="reset-password-confirm" type="password" required value={pw2}
                      onChange={(e) => setPw2(e.target.value)} placeholder="••••••••••"
                      className="mt-2 brutal-input w-full" />
                  </label>
                  <button type="submit" disabled={loading} data-testid="reset-submit-btn"
                    className="brutal-btn bg-ink text-white w-full hover:bg-[#2A2A2A] disabled:opacity-60">
                    {loading ? "Saving…" : "Set new password"}
                  </button>
                </form>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
