import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import DpaGate from "@/components/DpaGate";
import { homeForRole } from "@/lib/roleNavigation";

// Guards a route by role. Logged-out users go to /login; logged-in users of a
// disallowed role are bounced to their own home. The owner is a super-admin and
// is always allowed. This is a UX guard only — the API enforces real security.
export default function RoleRoute({ allow, children }) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  const allowed = user.role === "owner" || !allow || allow.includes(user.role);
  if (!allowed) {
    return <Navigate to={homeForRole(user.role)} replace />;
  }

  return <DpaGate>{children}</DpaGate>;
}
