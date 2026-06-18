import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import GlobalNav from "@/components/GlobalNav";
import GradeLevelSelect from "@/components/GradeLevelSelect";
import { GoogleLogo, Warning, ArrowRight, ArrowLeft } from "@phosphor-icons/react";
import { toast } from "sonner";

// 3-step signup: 1) email, 2) first name, 3) password + grade level
export default function Register() {
  const { registerWithEmail } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({ email: "", name: "", password: "", grade_level: "uk_y10" });
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const next = (e) => {
    e?.preventDefault();
    setErr("");
    if (step === 1) {
      if (!form.email.includes("@")) { setErr("Enter a valid email."); return; }
      setStep(2);
    } else if (step === 2) {
      if (!form.name.trim()) { setErr("Enter your first name."); return; }
      setStep(3);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    if (form.password.length < 10) { setErr("Password must be at least 10 characters."); return; }
    if (!/[A-Z]/.test(form.password) || !/[a-z]/.test(form.password) || !/\d/.test(form.password) || !/[!@#$%^&*()_+\-={}\[\]:;"'<>,.?/\\|`~]/.test(form.password)) {
      setErr("Password needs upper, lower, a number and a symbol."); return;
    }
    setLoading(true);
    try {
      await registerWithEmail(form);
      toast.success("Account created!");
      navigate("/dashboard", { replace: true });
    } catch (ex) {
      setErr(ex.response?.data?.detail || "Registration failed");
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
            <div className="flex items-center gap-2 mb-3">
              {[1, 2, 3].map((s) => (
                <div key={s} className={`h-2 flex-1 rounded-full border-2 border-ink ${step >= s ? "bg-ink" : "bg-white"}`} />
              ))}
            </div>

            <h1 className="font-display font-black text-3xl tracking-tight mb-2">
              {step === 1 ? "Enter your email" : step === 2 ? "What's your first name?" : "Create a password"}
            </h1>
            <p className="text-[#4A4A4A] mb-6 text-sm">
              {step === 1 && "We'll use this to send you study reminders. Use a school email if you have one."}
              {step === 2 && "We'll greet you with this on every page."}
              {step === 3 && "Pick a strong password — at least 10 characters with upper, lower, a number and a symbol."}
            </p>

            {err && (
              <div className="mb-4 border-2 border-focus bg-peach text-ink p-3 rounded-md flex items-center gap-2 text-sm" data-testid="register-error">
                <Warning size={18} weight="bold" /> {err}
              </div>
            )}

            {step === 1 && (
              <form onSubmit={next} className="space-y-4">
                <label className="block">
                  <span className="text-xs uppercase tracking-[0.2em] font-bold">Email</span>
                  <input
                    data-testid="register-email-input"
                    type="email" required autoFocus value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    className="mt-2 brutal-input w-full" placeholder="you@school.edu" />
                </label>
                <button type="submit" data-testid="register-next-btn"
                  className="brutal-btn bg-ink text-white w-full inline-flex items-center justify-center gap-2">
                  Continue <ArrowRight size={16} weight="bold" />
                </button>
              </form>
            )}

            {step === 2 && (
              <form onSubmit={next} className="space-y-4">
                <label className="block">
                  <span className="text-xs uppercase tracking-[0.2em] font-bold">First name</span>
                  <input
                    data-testid="register-name-input"
                    required autoFocus value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    className="mt-2 brutal-input w-full" placeholder="Ada" />
                </label>
                <div className="flex gap-2">
                  <button type="button" onClick={() => setStep(1)} className="brutal-btn bg-white inline-flex items-center gap-2"><ArrowLeft size={16} /> Back</button>
                  <button type="submit" data-testid="register-next-btn"
                    className="brutal-btn bg-ink text-white flex-1 inline-flex items-center justify-center gap-2">
                    Continue <ArrowRight size={16} weight="bold" />
                  </button>
                </div>
              </form>
            )}

            {step === 3 && (
              <form onSubmit={submit} className="space-y-4">
                <label className="block">
                  <span className="text-xs uppercase tracking-[0.2em] font-bold">Password</span>
                  <input
                    data-testid="register-password-input"
                    type="password" required autoFocus value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    className="mt-2 brutal-input w-full" placeholder="10+ chars · Aa1!" />
                </label>
                <label className="block">
                  <span className="text-xs uppercase tracking-[0.2em] font-bold">Grade / year level</span>
                  <GradeLevelSelect
                    testId="register-grade-select"
                    value={form.grade_level}
                    onChange={(v) => setForm({ ...form, grade_level: v })}
                    className="mt-2 w-full"
                  />
                </label>
                <div className="flex gap-2">
                  <button type="button" onClick={() => setStep(2)} className="brutal-btn bg-white inline-flex items-center gap-2"><ArrowLeft size={16} /> Back</button>
                  <button type="submit" disabled={loading} data-testid="register-submit-btn"
                    className="brutal-btn bg-ink text-white flex-1 disabled:opacity-60">
                    {loading ? "Creating…" : "Create account"}
                  </button>
                </div>
              </form>
            )}

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
            <p className="text-xs text-center mt-3 text-[#4A4A4A]">
              Registering a school?{" "}
              <Link to="/signup/school" className="font-bold underline underline-offset-4">School signup →</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
