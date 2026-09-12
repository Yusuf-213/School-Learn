import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Bell, Check } from "@phosphor-icons/react";

const POLL_MS = 60000;

function timeAgo(iso) {
  const s = Math.max(1, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 60) return `${s}s ago`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.round(h / 24)}d ago`;
}

export default function NotificationBell() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  const load = useCallback(async () => {
    if (!user) return;
    try {
      const { data } = await api.get("/notifications");
      setItems(data.items || []);
      setUnread(data.unread || 0);
    } catch {}
  }, [user]);

  useEffect(() => {
    if (!user) return;
    load();
    const t = setInterval(load, POLL_MS);
    return () => clearInterval(t);
  }, [user, load]);

  useEffect(() => {
    const onDoc = (e) => {
      if (!ref.current) return;
      if (!ref.current.contains(e.target)) setOpen(false);
    };
    if (open) document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  if (!user) return null;

  const handleClick = async (n) => {
    try { await api.post(`/notifications/${n.notification_id}/read`); } catch {}
    setOpen(false);
    if (n.url) navigate(n.url);
    load();
  };
  const markAll = async () => {
    try { await api.post("/notifications/read-all"); } catch {}
    load();
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        data-testid="notification-bell"
        aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
        className="relative brutal-btn bg-white p-2"
      >
        <Bell size={18} weight={unread ? "fill" : "regular"} />
        {unread > 0 && (
          <span
            data-testid="notification-unread-count"
            className="absolute -top-2 -right-2 min-w-[20px] h-5 px-1 rounded-full border-2 border-ink bg-focus text-white text-[10px] font-bold flex items-center justify-center"
          >
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>
      {open && (
        <div
          data-testid="notification-dropdown"
          className="absolute right-0 mt-2 w-[340px] max-w-[92vw] brutal-card p-0 bg-white z-50 overflow-hidden"
        >
          <div className="flex items-center justify-between p-3 border-b-2 border-ink bg-butter">
            <div className="text-xs uppercase tracking-[0.2em] font-bold">Notifications</div>
            {unread > 0 && (
              <button onClick={markAll} data-testid="notification-mark-all-read"
                className="text-xs underline inline-flex items-center gap-1">
                <Check size={12} weight="bold" /> Mark all read
              </button>
            )}
          </div>
          <div className="max-h-[420px] overflow-y-auto">
            {items.length === 0 ? (
              <div className="p-6 text-sm text-[#4A4A4A] text-center">You're all caught up.</div>
            ) : (
              items.map((n) => (
                <button
                  key={n.notification_id}
                  onClick={() => handleClick(n)}
                  data-testid={`notification-item-${n.notification_id}`}
                  className={`w-full text-left p-3 border-b border-ink/20 hover:bg-butter/60 ${n.read ? "" : "bg-lavender/40"}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="font-bold text-sm">{n.title}</div>
                    {!n.read && <span className="mt-1 w-2 h-2 rounded-full bg-focus shrink-0" />}
                  </div>
                  <div className="text-xs text-[#333] mt-0.5 line-clamp-2">{n.body}</div>
                  <div className="text-[10px] text-[#4A4A4A] mt-1 uppercase tracking-[0.1em] font-bold">{timeAgo(n.created_at)}</div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
