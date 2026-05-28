import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { GraduationCap, GoogleLogo, Envelope, Lock, Warning } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Login() {
  const { loginWithEmail } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const from = location.state?.from?.pathname || "/dashboard";

  const onSubmit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      await loginWithEmail(email, password);
      toast.success("Welcome back!");
      navigate(from, { replace: true });
    } catch (ex) {
      setErr(ex.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const onGoogle = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen bg-paper flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <Link to="/" className="flex items-center gap-2 mb-8 justify-center" data-testid="back-home-link">
          <div className="border-2 border-ink rounded-md bg-mint p-2 shadow-brutal"><GraduationCap size={22} weight="duotone" /></div>
          <span className="font-display font-black text-2xl tracking-tight">ScholarHub</span>
        </Link>

        <div className="brutal-card p-8">
          <h1 className="font-display font-black text-4xl tracking-tight mb-2">Welcome back.</h1>
          <p className="text-[#4A4A4A] mb-6">Sign in to keep your progress and continue learning.</p>

          {err && (
            <div className="mb-4 border-2 border-focus bg-peach text-ink p-3 rounded-md flex items-center gap-2 text-sm" data-testid="login-error">
              <Warning size={18} weight="bold" /> {err}
            </div>
          )}

          <form onSubmit={onSubmit} className="space-y-4">
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold flex items-center gap-2"><Envelope size={14} /> Email</span>
              <input
                data-testid="login-email-input"
                type="email" required value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@school.edu"
                className="mt-2 brutal-input w-full"
              />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold flex items-center gap-2"><Lock size={14} /> Password</span>
              <input
                data-testid="login-password-input"
                type="password" required value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="mt-2 brutal-input w-full"
              />
            </label>

            <button type="submit" disabled={loading} data-testid="login-submit-btn"
              className="brutal-btn bg-ink text-white w-full hover:bg-[#2A2A2A] disabled:opacity-60">
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <div className="flex items-center gap-3 my-6">
            <div className="h-px bg-ink flex-1" /><span className="text-xs uppercase tracking-[0.2em] font-bold">Or</span><div className="h-px bg-ink flex-1" />
          </div>

          <button onClick={onGoogle} data-testid="login-google-btn" className="brutal-btn bg-white hover:bg-butter w-full flex items-center justify-center gap-2">
            <GoogleLogo size={20} weight="bold" /> Continue with Google
          </button>

          <p className="text-sm mt-6 text-center">
            No account?{" "}
            <Link to="/register" className="font-bold underline underline-offset-4" data-testid="signup-link">Create one</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
