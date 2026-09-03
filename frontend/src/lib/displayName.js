// Deterministic, non-identifying display handle so we never render a user's
// real name/username/email in the UI. Same input -> same handle every render.

const ADJECTIVES = [
  "Bright", "Curious", "Focused", "Kind", "Bold", "Sharp", "Steady", "Quick",
  "Sunny", "Clever", "Calm", "Eager", "Fair", "Keen", "Merry", "Nimble",
];
const ANIMALS = [
  "Otter", "Owl", "Fox", "Wren", "Bear", "Lynx", "Kite", "Puma",
  "Heron", "Robin", "Badger", "Falcon", "Marten", "Osprey", "Stag", "Vole",
];

// Cheap deterministic 32-bit hash (djb2-ish).
function hash32(s = "") {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

/** Stable, on-brand pseudonym like "Bright Otter" — never leaks the real name. */
export function displayHandle(user) {
  if (!user) return "User";
  const seed = user.user_id || user.email || user.name || "anon";
  const h = hash32(seed);
  return `${ADJECTIVES[h % ADJECTIVES.length]} ${ANIMALS[Math.floor(h / ADJECTIVES.length) % ANIMALS.length]}`;
}

/** Single-letter avatar initial that isn't the user's real initial either. */
export function displayInitial(user) {
  return displayHandle(user)[0] || "U";
}
