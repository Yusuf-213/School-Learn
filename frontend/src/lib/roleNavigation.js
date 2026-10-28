// Canonical post-login landing page per role. Security is enforced on the
// backend; this only decides where to send the user first.
export const HOME_BY_ROLE = Object.freeze({
  owner: "/owner",
  school_admin: "/teacher",
  teacher: "/teacher",
  student: "/dashboard",
  parent: "/parent",
  individual: "/dashboard",
});

export function homeForRole(role) {
  return HOME_BY_ROLE[role] || "/dashboard";
}

// Shared role groups used by route guards.
export const STAFF_ROLES = ["owner", "school_admin", "teacher"];
export const OWNER_ONLY = ["owner"];
