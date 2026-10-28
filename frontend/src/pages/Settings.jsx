import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { NAV_SECTIONS, sectionVisible } from "@/lib/navSections";
import { toast } from "sonner";
import { Gear, SlidersHorizontal, Buildings, CircleNotch } from "@phosphor-icons/react";

function Toggle({ id, label, hint, checked, onChange, disabled }) {
  return (
    <label
      htmlFor={id}
      className={`flex items-center justify-between gap-4 p-3 rounded-md border-2 border-ink bg-white ${disabled ? "opacity-60" : "cursor-pointer"}`}
      data-testid={`toggle-row-${id}`}
    >
      <span>
        <span className="font-bold">{label}</span>
        {hint && <span className="block text-xs text-[#4A4A4A]">{hint}</span>}
      </span>
      <span className="relative inline-block shrink-0">
        <input
          id={id}
          type="checkbox"
          className="sr-only"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
          data-testid={`toggle-${id}`}
        />
        <span className={`block w-11 h-6 rounded-full border-2 border-ink transition-colors ${checked ? "bg-ink" : "bg-white"}`} />
        <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full border-2 border-ink transition-transform ${checked ? "translate-x-5 bg-mint" : "bg-white"}`} />
      </span>
    </label>
  );
}

export default function Settings() {
  const { user } = useAuth();
  const [prefs, setPrefs] = useState({});
  const [schoolDefaults, setSchoolDefaults] = useState({});
  const [loading, setLoading] = useState(true);
  const [savingUser, setSavingUser] = useState(false);
  const [savingSchool, setSavingSchool] = useState(false);

  const canSetSchoolDefault = user?.role === "owner" || user?.role === "school_admin";

  useEffect(() => {
    api.get("/me/nav-prefs")
      .then(({ data }) => {
        setPrefs(data.prefs || {});
        setSchoolDefaults(data.school_defaults || {});
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const saveUserPrefs = async (next) => {
    setPrefs(next);
    setSavingUser(true);
    try {
      await api.patch("/me/nav-prefs", { prefs: next });
      toast.success("Navigation updated");
    } catch {
      toast.error("Could not save — try again");
    } finally {
      setSavingUser(false);
    }
  };

  const toggleUserSection = (key, visible) => {
    saveUserPrefs({ ...prefs, [key]: visible });
  };

  const toggleSchoolDefault = async (key, visible) => {
    const next = { ...schoolDefaults, [key]: visible };
    setSchoolDefaults(next);
    setSavingSchool(true);
    try {
      await api.patch("/school/settings", { nav_section_defaults: next });
      toast.success("School-wide default updated");
    } catch {
      toast.error("Could not save school default");
    } finally {
      setSavingSchool(false);
    }
  };

  return (
    <AppLayout>
      <div className="space-y-8 max-w-3xl" data-testid="settings-page">
        <header>
          <div className="text-xs tracking-[0.2em] uppercase font-bold mb-2 text-[#4A4A4A] flex items-center gap-2">
            <Gear size={14} weight="fill" /> Settings
          </div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">Settings.</h1>
          <p className="text-[#4A4A4A] mt-3">Tailor your workspace. Turn off the sidebar sections you don't use.</p>
        </header>

        {loading ? (
          <div className="brutal-card p-8 flex items-center justify-center gap-2 text-[#4A4A4A]">
            <CircleNotch size={20} className="animate-spin" /> Loading…
          </div>
        ) : (
          <>
            <section className="brutal-card p-6 bg-white" data-testid="settings-nav-sections">
              <div className="flex items-center gap-2 mb-1">
                <SlidersHorizontal size={22} weight="bold" />
                <h2 className="font-display font-extrabold text-2xl">My navigation</h2>
              </div>
              <p className="text-sm text-[#4A4A4A] mb-4">
                Choose which sidebar sections appear for you. Home and Settings are always available.
                {savingUser && <span className="ml-2 inline-flex items-center gap-1"><CircleNotch size={12} className="animate-spin" /> saving…</span>}
              </p>
              <div className="space-y-2">
                {NAV_SECTIONS.map((s) => (
                  <Toggle
                    key={s.key}
                    id={`nav-${s.key}`}
                    label={s.label}
                    hint={s.hint}
                    checked={sectionVisible(s.key, prefs, schoolDefaults)}
                    onChange={(v) => toggleUserSection(s.key, v)}
                  />
                ))}
              </div>
            </section>

            {canSetSchoolDefault && (
              <section className="brutal-card p-6 bg-butter" data-testid="settings-school-defaults">
                <div className="flex items-center gap-2 mb-1">
                  <Buildings size={22} weight="bold" />
                  <h2 className="font-display font-extrabold text-2xl">School-wide defaults</h2>
                </div>
                <p className="text-sm text-[#4A4A4A] mb-4">
                  Set the starting sidebar for everyone in your school. Individual users can still override these for
                  themselves above.
                  {savingSchool && <span className="ml-2 inline-flex items-center gap-1"><CircleNotch size={12} className="animate-spin" /> saving…</span>}
                </p>
                <div className="space-y-2">
                  {NAV_SECTIONS.map((s) => (
                    <Toggle
                      key={s.key}
                      id={`school-nav-${s.key}`}
                      label={s.label}
                      hint={`Show the ${s.label} section by default`}
                      checked={schoolDefaults[s.key] !== false}
                      onChange={(v) => toggleSchoolDefault(s.key, v)}
                    />
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </AppLayout>
  );
}
