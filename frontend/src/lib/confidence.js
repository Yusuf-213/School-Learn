// Parse a trailing "Confidence: NN%" line out of an AI response and expose both parts.

const RX = /^\s*confidence\s*:\s*(\d{1,3})\s*%\s*\.?\s*$/im;

export function parseConfidence(text) {
  if (!text) return { text: "", confidence: null };
  const lines = String(text).trimEnd().split(/\r?\n/);
  // Search from the end; take the last line matching the pattern.
  for (let i = lines.length - 1; i >= 0; i--) {
    const l = lines[i];
    const m = l.match(RX);
    if (m) {
      const n = Math.max(0, Math.min(100, parseInt(m[1], 10)));
      const clean = lines.slice(0, i).join("\n").trimEnd();
      return { text: clean, confidence: n };
    }
    // Only skip trailing blank lines; if any real content is between the confidence line and the end, stop.
    if (l.trim() !== "") break;
  }
  return { text: String(text).trimEnd(), confidence: null };
}

/** Tailwind classes for a confidence pill based on the % value. */
export function confidenceStyle(n) {
  if (n === null || n === undefined) return { bg: "bg-white", label: "—" };
  if (n >= 85) return { bg: "bg-mint", label: `${n}% confident` };
  if (n >= 65) return { bg: "bg-butter", label: `${n}% confident` };
  if (n >= 40) return { bg: "bg-peach", label: `${n}% confident · double-check` };
  return { bg: "bg-red-200", label: `${n}% confident · verify with a teacher` };
}
