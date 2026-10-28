import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import GlobalNav from "@/components/GlobalNav";
import { Envelope, CheckCircle, Warning } from "@phosphor-icons/react";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const onSubmit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      await api.post("/auth/forgot-password", { email: email.trim(), origin_url: window.location.origin });
      setSent(true);
    } catch (ex) {
      setErr(ex.response?.data?.detail || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper">
      <GlobalNav />
      <div className="flex items-center justify-center p-6 py-10">
        <div className="w-full max-w-md">
          <div className="brutal-card p-8" data-testid="forgot-password-page">
            <h1 className="font-display font-black text-4xl tracking-tight mb-2">Reset password.</h1>
            {sent ? (
              <div className="space-y-4" data-testid="forgot-password-sent">
                <div className="border-2 border-ink bg-mint p-4 rounded-md flex items-start gap-2 text-sm">
                  <CheckCircle size={20} weight="fill" className="mt-0.5 shrink-0" />
                  <span>If an account exists for <strong>{email}</strong>, we've sent a link to reset your password. It expires in 60 minutes — check your inbox and spam folder.</span>
                </div>
                <Link to="/login" className="brutal-btn bg-ink text-white w-full inline-block text-center" data-testid="back-to-login">Back to sign in</Link>
              </div>
            ) : (
              <>
                <p className="text-[#4A4A4A] mb-6">Enter your account email and we'll send you a link to set a new password.</p>
                {err && (
                  <div className="mb-4 border-2 border-focus bg-peach text-ink p-3 rounded-md flex items-center gap-2 text-sm" data-testid="forgot-password-error">
                    <Warning size={18} weight="bold" /> {err}
                  </div>
                )}
                <form onSubmit={onSubmit} className="space-y-4">
                  <label className="block">
                    <span className="text-xs uppercase tracking-[0.2em] font-bold flex items-center gap-2"><Envelope size={14} /> Email</span>
                    <input data-testid="forgot-email-input" type="email" required value={email}
                      onChange={(e) => setEmail(e.target.value)} placeholder="you@school.edu"
                      className="mt-2 brutal-input w-full" />
                  </label>
                  <button type="submit" disabled={loading} data-testid="forgot-submit-btn"
                    className="brutal-btn bg-ink text-white w-full hover:bg-[#2A2A2A] disabled:opacity-60">
                    {loading ? "Sending…" : "Send reset link"}
                  </button>
                </form>
                <p className="text-sm mt-6 text-center">
                  Remembered it?{" "}
                  <Link to="/login" className="font-bold underline underline-offset-4" data-testid="login-link">Back to sign in</Link>
                </p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
