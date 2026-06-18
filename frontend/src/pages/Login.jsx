import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import GlobalNav from "@/components/GlobalNav";
import { GoogleLogo, Envelope, Lock, Warning, User } from "@phosphor-icons/react";

export default function Login() {
  const { loginWithEmail, setUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const from = location.state?.from?.pathname || "/dashboard";

  const onSubmit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      // Allow username OR email login
      if (identifier.includes("@")) {
        await loginWithEmail(identifier, password);
      } else {
        const { data } = await api.post("/auth/login_username", { identifier, password });
        localStorage.setItem("token", data.token);
        setUser(data.user);
      }
      navigate(from, { replace: true });
    } catch (ex) {
      setErr(ex.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const onGoogle = () => {
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen bg-paper">
      <GlobalNav />
      <div className="flex items-center justify-center p-6 py-10">
        <div className="w-full max-w-md">
          <div className="brutal-card p-8">
            <h1 className="font-display font-black text-4xl tracking-tight mb-2">Welcome back.</h1>
            <p className="text-[#4A4A4A] mb-6">Sign in with your email, school email, or username.</p>

            {err && (
              <div className="mb-4 border-2 border-focus bg-peach text-ink p-3 rounded-md flex items-center gap-2 text-sm" data-testid="login-error">
                <Warning size={18} weight="bold" /> {err}
              </div>
            )}

            <form onSubmit={onSubmit} className="space-y-4">
              <label className="block">
                <span className="text-xs uppercase tracking-[0.2em] font-bold flex items-center gap-2"><User size={14} /> Email or username</span>
                <input
                  data-testid="login-email-input"
                  required value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="you@school.edu  or  Yusufm_1"
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

            <div className="text-sm mt-6 text-center space-y-2">
              <p>
                Student or teacher?{" "}
                <Link to="/register" className="font-bold underline underline-offset-4" data-testid="signup-link">Create individual account</Link>
              </p>
              <p>
                Are you a school?{" "}
                <Link to="/signup/school" className="font-bold underline underline-offset-4" data-testid="school-signup-link">Register your school</Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
