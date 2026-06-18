import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;
const USER_KEY = "scholarhub_user";

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => {
    // Auto-rotate the JWT if the backend sent a fresh one
    const refreshed = r.headers["x-refresh-token"] || r.headers["X-Refresh-Token"];
    if (refreshed) localStorage.setItem("token", refreshed);
    return r;
  },
  (err) => {
    // Hard-clear local session ONLY on a real 401 from the API.
    // Do not clear on network failures, 5xx, or aborts — those keep the user logged in.
    if (err?.response?.status === 401) {
      const url = err.config?.url || "";
      // Don't clear during the login attempt itself
      if (!url.includes("/auth/login") && !url.includes("/auth/register")) {
        localStorage.removeItem("token");
        localStorage.removeItem(USER_KEY);
      }
    }
    return Promise.reject(err);
  }
);
