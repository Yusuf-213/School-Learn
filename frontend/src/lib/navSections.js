// Collapsible sidebar sections. Keys are shared between SideNav (rendering)
// and Settings (toggles), and persisted to the backend as visibility prefs.
export const NAV_SECTIONS = [
  { key: "learn", label: "Learn", hint: "Lessons, homework, assessments & progress" },
  { key: "teach", label: "Teach", hint: "Teaching tools, rosters & parent access" },
  { key: "school", label: "School", hint: "Owner HQ, compliance & payouts" },
  { key: "account", label: "Account", hint: "Dreams, feedback, plans & settings" },
];

// A section is visible unless the user explicitly hid it; if the user has no
// preference the owner's school-wide default applies; otherwise visible.
export function sectionVisible(key, prefs, schoolDefaults) {
  if (prefs && Object.prototype.hasOwnProperty.call(prefs, key)) return prefs[key];
  if (schoolDefaults && Object.prototype.hasOwnProperty.call(schoolDefaults, key)) {
    return schoolDefaults[key];
  }
  return true;
}

// Which sections actually exist for a given role (mirrors SideNav.buildNav).
export function sectionsForRole(role) {
  if (role === "parent") return ["account"];
  if (role === "owner") return ["learn", "teach", "school", "account"];
  if (role === "teacher" || role === "school_admin") return ["learn", "teach", "account"];
  return ["learn", "account"]; // student, individual
}
