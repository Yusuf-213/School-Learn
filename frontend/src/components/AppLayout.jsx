import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  House, BookOpen, Timer, ChartLine, SignOut, GraduationCap, List, X, CreditCard,
} from "@phosphor-icons/react";
import { useState } from "react";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: House, testid: "nav-dashboard" },
  { to: "/subjects", label: "Subjects", icon: BookOpen, testid: "nav-subjects" },
  { to: "/focus", label: "Focus Mode", icon: Timer, testid: "nav-focus" },
  { to: "/progress", label: "Progress", icon: ChartLine, testid: "nav-progress" },
  { to: "/pricing", label: "Plans", icon: CreditCard, testid: "nav-pricing" },
];

export default function AppLayout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-paper text-ink">
      {/* Mobile top bar */}
      <div className="md:hidden flex items-center justify-between border-b-2 border-ink bg-white px-4 py-3 sticky top-0 z-30">
        <div className="flex items-center gap-2">
          <GraduationCap size={26} weight="duotone" />
          <span className="font-display font-black text-xl">ScholarHub</span>
        </div>
        <button
          data-testid="mobile-menu-toggle"
          onClick={() => setOpen(!open)}
          className="border-2 border-ink rounded-md p-2 bg-butter shadow-brutal"
        >
          {open ? <X size={20} /> : <List size={20} />}
        </button>
      </div>

      <div className="flex">
        {/* Sidebar */}
        <aside
          className={`${open ? "block" : "hidden"} md:block w-full md:w-64 shrink-0 md:sticky md:top-0 md:h-screen border-r-2 border-ink bg-white p-6`}
          data-testid="app-sidebar"
        >
          <div className="hidden md:flex items-center gap-2 mb-10">
            <div className="border-2 border-ink rounded-md bg-mint p-2 shadow-brutal">
              <GraduationCap size={24} weight="duotone" />
            </div>
            <span className="font-display font-black text-2xl tracking-tight">ScholarHub</span>
          </div>

          <nav className="space-y-2">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setOpen(false)}
                data-testid={item.testid}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-3 rounded-md border-2 transition-all duration-150 font-bold ${
                    isActive
                      ? "border-ink bg-butter shadow-brutal"
                      : "border-transparent hover:border-ink hover:bg-mint hover:-translate-y-0.5"
                  }`
                }
              >
                <item.icon size={20} weight="duotone" />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="mt-10 border-t-2 border-ink pt-6">
            <div className="flex items-center gap-3 mb-4">
              {user?.picture ? (
                <img src={user.picture} alt="" className="w-10 h-10 rounded-full border-2 border-ink" />
              ) : (
                <div className="w-10 h-10 rounded-full border-2 border-ink bg-peach flex items-center justify-center font-bold">
                  {user?.name?.[0]?.toUpperCase() || "U"}
                </div>
              )}
              <div className="overflow-hidden">
                <div className="font-bold truncate" data-testid="sidebar-user-name">{user?.name}</div>
                <div className="text-xs text-muted-foreground truncate">{user?.email}</div>
              </div>
            </div>
            <button
              data-testid="logout-btn"
              onClick={handleLogout}
              className="w-full flex items-center justify-center gap-2 brutal-btn bg-white hover:bg-peach"
            >
              <SignOut size={18} weight="bold" /> Sign out
            </button>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 min-w-0 p-6 md:p-10">
          {children}
        </main>
      </div>
    </div>
  );
}
