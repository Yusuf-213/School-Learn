import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";

const AuthContext = createContext(null);
const USER_KEY = "scholarhub_user";

function readCachedUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeCachedUser(user) {
  try {
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
    else localStorage.removeItem(USER_KEY);
  } catch {}
}

export function AuthProvider({ children }) {
  // Initialize user from localStorage IMMEDIATELY — no loading flash, no false redirect on refresh.
  const [user, setUserState] = useState(() => readCachedUser());
  const [loading, setLoading] = useState(false);

  const setUser = useCallback((u) => {
    setUserState(u);
    writeCachedUser(u);
  }, []);

  const checkAuth = useCallback(async () => {
    const hasToken = typeof window !== "undefined" && localStorage.getItem("token");
    const hasCookie = typeof document !== "undefined" && document.cookie.includes("session_token");
    if (!hasToken && !hasCookie) {
      setUser(null);
      return;
    }
    try {
      const res = await api.get("/auth/me");
      setUser(res.data);
      // Persist refreshed JWT if backend rotated it
      const refreshed = res.headers["x-refresh-token"] || res.headers["X-Refresh-Token"];
      if (refreshed) localStorage.setItem("token", refreshed);
    } catch (err) {
      // ONLY clear the session on an explicit 401. Network blips and 5xx keep the user logged in.
      if (err?.response?.status === 401) {
        localStorage.removeItem("token");
        setUser(null);
      }
    }
  }, [setUser]);

  useEffect(() => {
    // Skip background probe if returning from Emergent OAuth callback
    if (typeof window !== "undefined" && window.location.hash?.includes("session_id=")) {
      return;
    }
    // Validate in background — does not gate the UI.
    checkAuth();
  }, [checkAuth]);

  const loginWithEmail = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("token", data.token);
    setUser(data.user);
    return data.user;
  };

  const registerWithEmail = async (payload) => {
    const { data } = await api.post("/auth/register", payload);
    localStorage.setItem("token", data.token);
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch {}
    localStorage.removeItem("token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, loginWithEmail, registerWithEmail, logout, refreshUser: checkAuth, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
