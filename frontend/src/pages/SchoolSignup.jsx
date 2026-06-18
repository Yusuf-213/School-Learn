import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import GlobalNav from "@/components/GlobalNav";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Buildings, ArrowRight, ArrowLeft, Warning, CheckCircle } from "@phosphor-icons/react";
import { toast } from "sonner";

const PLAN_OPTIONS = [
  { id: "school_small", label: "Small school (600–1,000 students)", price: "£750/year" },
  { id: "school_medium", label: "Medium school (750–1,500 students)", price: "£1,500/year" },
  { id: "school_large", label: "Large school (1,500+ students)", price: "£3,000/year" },
];

export default function SchoolSignup() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    school_name: "",
    school_email_domain: "",
    contact_name: "",
    contact_email: "",
    contact_password: "",
    approx_students: 800,
    students_per_class: 30,
    class_names_raw: "",
    slt_emails_raw: "",
    plan_id: "school_small",
  });

  const next = (e) => {
    e?.preventDefault();
    setErr("");
    if (step === 1) {
      if (!form.school_name.trim()) return setErr("School name required.");
      if (!form.school_email_domain.trim() || form.school_email_domain.includes("@")) return setErr("Domain only, e.g., elmwood.sch.uk");
    }
    if (step === 2) {
      if (form.approx_students < 1) return setErr("Approximate student count required.");
      if (form.students_per_class < 1) return setErr("Students per class required.");
      if (!form.class_names_raw.trim()) return setErr("List at least one class.");
    }
    if (step === 3) {
      if (!form.contact_name.trim()) return setErr("Contact name required.");
      if (!form.contact_email.includes("@" + form.school_email_domain)) {
        return setErr(`Contact email must end with @${form.school_email_domain}.`);
      }
      if (form.contact_password.length < 6) return setErr("Password must be at least 6 characters.");
    }
    setStep((s) => s + 1);
  };

  const submit = async (e) => {
    e?.preventDefault();
    setErr("");
    setLoading(true);
    try {
      const payload = {
        school_name: form.school_name,
        school_email_domain: form.school_email_domain.trim().toLowerCase().replace(/^@/, ""),
        contact_name: form.contact_name,
        contact_email: form.contact_email.toLowerCase(),
        contact_password: form.contact_password,
        approx_students: Number(form.approx_students),
        students_per_class: Number(form.students_per_class),
        class_names: form.class_names_raw.split(/[\n,]+/).map((s) => s.trim()).filter(Boolean),
        slt_emails: form.slt_emails_raw.split(/[\n,]+/).map((s) => s.trim()).filter(Boolean),
        plan_id: form.plan_id,
      };
      const { data } = await api.post("/auth/signup_school", payload);
      localStorage.setItem("token", data.token);
      setUser(data.user);
      toast.success("School registered! Set up your subscription next.");
      navigate("/pricing");
    } catch (ex) {
      setErr(ex.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper">
      <GlobalNav />
      <div className="max-w-2xl mx-auto px-6 py-10">
        <div className="mb-6">
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A]">Register your school</div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Bring Learnify to your school.</h1>
          <p className="text-[#4A4A4A] mt-3">Replace Sparx, Bedrock, Seneca and Teams with one system. We'll get you set up in five minutes — payment is the last step.</p>
        </div>

        <div className="flex items-center gap-2 mb-6">
          {[1, 2, 3, 4].map((s) => (
            <div key={s} className={`h-2 flex-1 rounded-full border-2 border-ink ${step >= s ? "bg-ink" : "bg-white"}`} />
          ))}
        </div>

        <div className="brutal-card p-8">
          {err && (
            <div className="mb-4 border-2 border-focus bg-peach text-ink p-3 rounded-md flex items-center gap-2 text-sm" data-testid="school-error">
              <Warning size={18} weight="bold" /> {err}
            </div>
          )}

          {step === 1 && (
            <form onSubmit={next} className="space-y-4">
              <h2 className="font-display font-bold text-2xl">Step 1 — School details</h2>
              <label className="block">
                <span className="text-xs uppercase tracking-[0.2em] font-bold">School name</span>
                <input data-testid="school-name-input" required value={form.school_name}
                  onChange={(e) => setForm({ ...form, school_name: e.target.value })}
                  className="mt-2 brutal-input w-full" placeholder="Elmwood Secondary School" />
              </label>
              <label className="block">
                <span className="text-xs uppercase tracking-[0.2em] font-bold">School email domain</span>
                <input data-testid="school-domain-input" required value={form.school_email_domain}
                  onChange={(e) => setForm({ ...form, school_email_domain: e.target.value })}
                  className="mt-2 brutal-input w-full" placeholder="elmwood.sch.uk" />
                <span className="text-xs text-[#4A4A4A] inline-block mt-1">Students and teachers will sign in with @{form.school_email_domain || "school.uk"} addresses.</span>
              </label>
              <button type="submit" data-testid="school-next-1" className="brutal-btn bg-ink text-white w-full inline-flex items-center justify-center gap-2">
                Continue <ArrowRight size={16} weight="bold" />
              </button>
            </form>
          )}

          {step === 2 && (
            <form onSubmit={next} className="space-y-4">
              <h2 className="font-display font-bold text-2xl">Step 2 — Size & classes</h2>
              <div className="grid sm:grid-cols-2 gap-3">
                <label className="block">
                  <span className="text-xs uppercase tracking-[0.2em] font-bold">Approx students</span>
                  <input data-testid="school-students-input" type="number" min={1} value={form.approx_students}
                    onChange={(e) => setForm({ ...form, approx_students: e.target.value })}
                    className="mt-2 brutal-input w-full" />
                </label>
                <label className="block">
                  <span className="text-xs uppercase tracking-[0.2em] font-bold">Students per class</span>
                  <input data-testid="school-class-size-input" type="number" min={1} value={form.students_per_class}
                    onChange={(e) => setForm({ ...form, students_per_class: e.target.value })}
                    className="mt-2 brutal-input w-full" />
                </label>
              </div>
              <label className="block">
                <span className="text-xs uppercase tracking-[0.2em] font-bold">Class names (comma or newline separated)</span>
                <textarea data-testid="school-classes-input" rows={4} value={form.class_names_raw}
                  onChange={(e) => setForm({ ...form, class_names_raw: e.target.value })}
                  className="mt-2 brutal-input w-full font-mono text-sm"
                  placeholder="8x1, 8x2, 8y6&#10;9x1, 9y6" />
                <span className="text-xs text-[#4A4A4A] inline-block mt-1">e.g., <code>8x1, 9y6, 10z3</code></span>
              </label>
              <div className="flex gap-2">
                <button type="button" onClick={() => setStep(1)} className="brutal-btn bg-white inline-flex items-center gap-2"><ArrowLeft size={16} /> Back</button>
                <button type="submit" data-testid="school-next-2" className="brutal-btn bg-ink text-white flex-1 inline-flex items-center justify-center gap-2">
                  Continue <ArrowRight size={16} weight="bold" />
                </button>
              </div>
            </form>
          )}

          {step === 3 && (
            <form onSubmit={next} className="space-y-4">
              <h2 className="font-display font-bold text-2xl">Step 3 — School lead</h2>
              <label className="block">
                <span className="text-xs uppercase tracking-[0.2em] font-bold">Your full name (head teacher or admin)</span>
                <input data-testid="school-contact-name" required value={form.contact_name}
                  onChange={(e) => setForm({ ...form, contact_name: e.target.value })}
                  className="mt-2 brutal-input w-full" placeholder="Jane Smith" />
              </label>
              <label className="block">
                <span className="text-xs uppercase tracking-[0.2em] font-bold">Your school email</span>
                <input data-testid="school-contact-email" type="email" required value={form.contact_email}
                  onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
                  className="mt-2 brutal-input w-full" placeholder={`head@${form.school_email_domain || "school.uk"}`} />
              </label>
              <label className="block">
                <span className="text-xs uppercase tracking-[0.2em] font-bold">Password</span>
                <input data-testid="school-contact-password" type="password" required value={form.contact_password}
                  onChange={(e) => setForm({ ...form, contact_password: e.target.value })}
                  className="mt-2 brutal-input w-full" placeholder="At least 6 characters" />
              </label>
              <label className="block">
                <span className="text-xs uppercase tracking-[0.2em] font-bold">SLT email addresses (one per line, optional)</span>
                <textarea data-testid="school-slt-input" rows={3} value={form.slt_emails_raw}
                  onChange={(e) => setForm({ ...form, slt_emails_raw: e.target.value })}
                  className="mt-2 brutal-input w-full font-mono text-sm"
                  placeholder={`deputy@${form.school_email_domain || "school.uk"}\nhead.maths@${form.school_email_domain || "school.uk"}`} />
              </label>
              <div className="flex gap-2">
                <button type="button" onClick={() => setStep(2)} className="brutal-btn bg-white inline-flex items-center gap-2"><ArrowLeft size={16} /> Back</button>
                <button type="submit" data-testid="school-next-3" className="brutal-btn bg-ink text-white flex-1 inline-flex items-center justify-center gap-2">
                  Continue <ArrowRight size={16} weight="bold" />
                </button>
              </div>
            </form>
          )}

          {step === 4 && (
            <form onSubmit={submit} className="space-y-4">
              <h2 className="font-display font-bold text-2xl">Step 4 — Pick a plan</h2>
              <p className="text-sm text-[#4A4A4A]">You'll set up Stripe payment right after creating the account. Annual price, billed once.</p>

              <div className="space-y-3">
                {PLAN_OPTIONS.map((p) => (
                  <label key={p.id} className={`flex items-center gap-3 border-2 border-ink rounded-md p-4 cursor-pointer transition-all ${form.plan_id === p.id ? "bg-butter shadow-brutal" : "bg-white hover:bg-mint"}`} data-testid={`school-plan-${p.id}`}>
                    <input type="radio" name="plan" value={p.id} checked={form.plan_id === p.id}
                      onChange={(e) => setForm({ ...form, plan_id: e.target.value })} className="sr-only" />
                    <div className={`w-5 h-5 rounded-full border-2 border-ink ${form.plan_id === p.id ? "bg-ink" : "bg-white"}`} />
                    <div className="flex-1">
                      <div className="font-display font-bold">{p.label}</div>
                      <div className="text-sm text-[#4A4A4A]">{p.price}</div>
                    </div>
                    {form.plan_id === p.id && <CheckCircle size={20} weight="fill" />}
                  </label>
                ))}
              </div>

              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setStep(3)} className="brutal-btn bg-white inline-flex items-center gap-2"><ArrowLeft size={16} /> Back</button>
                <button type="submit" disabled={loading} data-testid="school-submit-btn" className="brutal-btn bg-ink text-white flex-1 inline-flex items-center justify-center gap-2 disabled:opacity-60">
                  <Buildings size={18} weight="bold" /> {loading ? "Creating…" : "Create school account"}
                </button>
              </div>
            </form>
          )}
        </div>

        <p className="text-sm text-center mt-6">
          Already registered? <Link to="/login" className="font-bold underline underline-offset-4">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
