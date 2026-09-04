// Display the user's real name / username exactly as they set it up.
// (Previously this file returned a randomised pseudonym; removed 2026-02-04 per
// user request — schools want to see who they're actually looking at.)

export function displayHandle(user) {
  if (!user) return "User";
  const first = (user.name || "").trim().split(/\s+/)[0];
  return first || user.username || (user.email ? user.email.split("@")[0] : "User");
}

export function displayInitial(user) {
  const h = displayHandle(user);
  return (h[0] || "U").toUpperCase();
}
