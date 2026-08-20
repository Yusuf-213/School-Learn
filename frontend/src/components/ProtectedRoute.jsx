import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import DpaGate from "@/components/DpaGate";

export default function ProtectedRoute({ children }) {
  const { user } = useAuth();
  const location = useLocation();
  // User is hydrated synchronously from localStorage, so no loading flash.
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <DpaGate>{children}</DpaGate>;
}
