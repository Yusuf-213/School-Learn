// Mirror of backend curriculum_data.can_use_calculator — keeps calc features hidden
// for Reception through Year 5, allows from Year 6 onwards.
// Kept in sync with /api/curriculum/calculator-allowed.

const CALC_DENIED = new Set([
  "uk_reception", "uk_y1", "uk_y2", "uk_y3", "uk_y4", "uk_y5",
]);

export function canUseCalculator(gradeLevel) {
  if (!gradeLevel) return true; // adults / non-primary default to allowed
  return !CALC_DENIED.has(gradeLevel);
}

export function calcDenyReason() {
  return "Calculator features are hidden until end of KS2 (Year 6) per DfE guidance.";
}
