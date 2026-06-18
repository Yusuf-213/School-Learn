import { useEffect, useState } from "react";
import { Eye, TextAa, ArrowsClockwise, Gear, X } from "@phosphor-icons/react";

const KEY = "learnify_a11y";

function readPrefs() {
  try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch { return {}; }
}
function applyPrefs(p) {
  const root = document.documentElement;
  root.classList.toggle("a11y-dyslexia", !!p.dyslexia);
  root.classList.toggle("a11y-high-contrast", !!p.highContrast);
  root.classList.toggle("a11y-large-text", !!p.largeText);
  root.classList.toggle("a11y-reduce-motion", !!p.reduceMotion);
}

export function applyA11yOnLoad() {
  applyPrefs(readPrefs());
}

export default function AccessibilityMenu() {
  const [open, setOpen] = useState(false);
  const [p, setP] = useState(readPrefs());
  useEffect(() => { applyPrefs(p); localStorage.setItem(KEY, JSON.stringify(p)); }, [p]);

  return (
    <>
      <button onClick={() => setOpen(true)} data-testid="a11y-open"
        className="brutal-btn bg-white hover:bg-butter text-sm py-1.5 px-2.5 inline-flex items-center gap-1.5"
        aria-label="Accessibility options" title="Accessibility">
        <Eye size={16} weight="bold" />
      </button>

      {open && (
        <div className="fixed inset-0 z-[60] flex items-end md:items-center md:justify-center" data-testid="a11y-panel">
          <div className="absolute inset-0 bg-ink/60" onClick={() => setOpen(false)} />
          <div className="relative bg-paper border-2 border-ink rounded-t-lg md:rounded-lg shadow-brutal-xl w-full md:w-[440px] max-h-[80vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Gear size={20} weight="duotone" />
                <h2 className="font-display font-extrabold text-2xl">Accessibility</h2>
              </div>
              <button onClick={() => setOpen(false)} className="brutal-btn bg-white p-2" aria-label="Close" data-testid="a11y-close">
                <X size={16} />
              </button>
            </div>
            <Toggle id="dyslexia" label="Dyslexia-friendly font" hint="Use OpenDyslexic across the app" checked={!!p.dyslexia} onChange={(v) => setP({ ...p, dyslexia: v })} />
            <Toggle id="contrast" label="High contrast" hint="Stronger borders and pure colours" checked={!!p.highContrast} onChange={(v) => setP({ ...p, highContrast: v })} />
            <Toggle id="largetext" label="Larger text" hint="Increase base text size by 25%" checked={!!p.largeText} onChange={(v) => setP({ ...p, largeText: v })} />
            <Toggle id="motion" label="Reduce motion" hint="Disable animations and transitions" checked={!!p.reduceMotion} onChange={(v) => setP({ ...p, reduceMotion: v })} />
            <button onClick={() => setP({})} data-testid="a11y-reset"
              className="brutal-btn bg-white inline-flex items-center gap-2 mt-2 text-sm">
              <ArrowsClockwise size={14} weight="bold" /> Reset to defaults
            </button>
            <p className="text-xs text-[#4A4A4A] mt-4">Settings are saved on this device. WCAG 2.2 AA features.</p>
          </div>
        </div>
      )}
    </>
  );
}

function Toggle({ id, label, hint, checked, onChange }) {
  return (
    <label className="flex items-center justify-between gap-4 py-3 border-b border-ink/10 cursor-pointer" htmlFor={id}>
      <span>
        <span className="font-bold">{label}</span>
        <span className="block text-xs text-[#4A4A4A]">{hint}</span>
      </span>
      <span className="relative inline-block" data-testid={`a11y-toggle-${id}`}>
        <input id={id} type="checkbox" className="sr-only" checked={checked} onChange={(e) => onChange(e.target.checked)} />
        <span className={`block w-11 h-6 rounded-full border-2 border-ink transition-colors ${checked ? "bg-ink" : "bg-white"}`} />
        <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full border-2 border-ink transition-transform ${checked ? "translate-x-5 bg-mint" : "bg-white"}`} />
      </span>
    </label>
  );
}
