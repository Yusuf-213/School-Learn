import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import GlobalNav from "@/components/GlobalNav";
import GradeLevelSelect from "@/components/GradeLevelSelect";
import { GraduationCap, GoogleLogo, Warning } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Register() {
  const { registerWithEmail } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", grade_level: "high_school" });
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setErr("");
    if (form.password.length < 6) { setErr("Password must be at least 6 characters."); return; }
    setLoading(true);
    try {
      await registerWithEmail(form);
      toast.success("Account created! Welcome.");
      navigate("/dashboard", { replace: true });
    } catch (ex) {
      setErr(ex.response?.data?.detail || "Registration failed");
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
    <div className="min-h-screen bg-paper">
      <GlobalNav />
      <div className="flex items-center justify-center p-6 py-10">
        <div className="w-full max-w-md">
        <div className="brutal-card p-8">
          <h1 className="font-display font-black text-4xl tracking-tight mb-2">Create your account.</h1>
          <p className="text-[#4A4A4A] mb-6">Pick a grade level — we'll adapt every lesson to it.</p>

          {err && (
            <div className="mb-4 border-2 border-focus bg-peach text-ink p-3 rounded-md flex items-center gap-2 text-sm" data-testid="register-error">
              <Warning size={18} weight="bold" /> {err}
            </div>
          )}

          <form onSubmit={onSubmit} className="space-y-4">
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Full name</span>
              <input data-testid="register-name-input" required value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="mt-2 brutal-input w-full" placeholder="Ada Lovelace" />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Email</span>
              <input data-testid="register-email-input" type="email" required value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="mt-2 brutal-input w-full" placeholder="you@school.edu" />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Password</span>
              <input data-testid="register-password-input" type="password" required value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="mt-2 brutal-input w-full" placeholder="At least 6 characters" />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-[0.2em] font-bold">Grade / year level</span>
              <GradeLevelSelect
                testId="register-grade-select"
                value={form.grade_level}
                onChange={(v) => setForm({ ...form, grade_level: v })}
                className="mt-2 w-full"
              />
              <span className="text-xs text-[#4A4A4A] mt-1 inline-block">Pick the closest match — we calibrate every lesson to it.</span>
            </label>

            <button type="submit" disabled={loading} data-testid="register-submit-btn"
              className="brutal-btn bg-ink text-white w-full hover:bg-[#2A2A2A] disabled:opacity-60">
              {loading ? "Creating…" : "Create account"}
            </button>
          </form>

          <div className="flex items-center gap-3 my-6">
            <div className="h-px bg-ink flex-1" /><span className="text-xs uppercase tracking-[0.2em] font-bold">Or</span><div className="h-px bg-ink flex-1" />
          </div>

          <button onClick={onGoogle} data-testid="register-google-btn" className="brutal-btn bg-white hover:bg-butter w-full flex items-center justify-center gap-2">
            <GoogleLogo size={20} weight="bold" /> Sign up with Google
          </button>

          <p className="text-sm mt-6 text-center">
            Have an account?{" "}
            <Link to="/login" className="font-bold underline underline-offset-4" data-testid="login-link">Sign in</Link>
          </p>
        </div>
        </div>
      </div>
    </div>
  );
}
