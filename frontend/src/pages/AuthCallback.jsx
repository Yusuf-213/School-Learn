import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function AuthCallback() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const run = async () => {
      const hash = window.location.hash || "";
      const match = hash.match(/session_id=([^&]+)/);
      const session_id = match?.[1];
      if (!session_id) {
        navigate("/login", { replace: true });
        return;
      }
      try {
        const { data } = await api.post("/auth/session", { session_id });
        setUser(data.user);
        window.history.replaceState({}, "", "/dashboard");
        navigate("/dashboard", { replace: true, state: { user: data.user } });
      } catch (e) {
        navigate("/login", { replace: true });
      }
    };
    run();
  }, [navigate, setUser]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper" data-testid="auth-callback">
      <div className="brutal-card p-6 bg-butter">
        <div className="font-mono text-sm">Signing you in…</div>
      </div>
    </div>
  );
}
