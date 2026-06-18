import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { GraduationCap, House, BookOpen, Timer, ChartLine, CreditCard, Question, SignIn, List, X, SignOut, ChalkboardTeacher, Compass, Chat, Crown, Trophy, ShieldCheck } from "@phosphor-icons/react";
import { useState } from "react";
import AccessibilityMenu from "@/components/AccessibilityMenu";

const PUBLIC_LINKS = [
  { to: "/", label: "Home", icon: House, testid: "nav-home", end: true },
  { to: "/subjects", label: "Classes", icon: BookOpen, testid: "nav-classes" },
  { to: "/help", label: "Homework Help", icon: Question, testid: "nav-help" },
  { to: "/pricing", label: "Plans", icon: CreditCard, testid: "nav-plans" },
];

function navForUser(user) {
  if (!user) return PUBLIC_LINKS;

  const base = [
    { to: "/dashboard", label: "Dashboard", icon: House, testid: "nav-home", end: true },
    { to: "/subjects", label: "Classes", icon: BookOpen, testid: "nav-classes" },
    { to: "/help", label: "Homework Help", icon: Question, testid: "nav-help" },
    { to: "/dreams", label: "Dreams", icon: Compass, testid: "nav-dreams" },
  ];

  if (user.role === "owner") {
    return [
      { to: "/owner", label: "Owner HQ", icon: Crown, testid: "nav-owner" },
      ...base,
      { to: "/suggestions", label: "Suggestions", icon: Chat, testid: "nav-suggestions" },
      { to: "/pricing", label: "Plans", icon: CreditCard, testid: "nav-plans" },
    ];
  }
  if (user.role === "school_admin" || user.role === "teacher") {
    return [
      ...base,
      { to: "/teacher", label: "Teach", icon: ChalkboardTeacher, testid: "nav-teacher" },
      { to: "/focus", label: "Focus", icon: Timer, testid: "nav-focus" },
      { to: "/suggestions", label: "Feedback", icon: Chat, testid: "nav-suggestions" },
      { to: "/pricing", label: "Plans", icon: CreditCard, testid: "nav-plans" },
    ];
  }
  if (user.role === "student") {
    return [
      ...base,
      { to: "/my-record", label: "My record", icon: Trophy, testid: "nav-myrecord" },
      { to: "/focus", label: "Focus", icon: Timer, testid: "nav-focus" },
      { to: "/suggestions", label: "Suggestions", icon: Chat, testid: "nav-suggestions" },
    ];
  }
  // individual
  return [
    ...base,
    { to: "/focus", label: "Focus", icon: Timer, testid: "nav-focus" },
    { to: "/progress", label: "Progress", icon: ChartLine, testid: "nav-progress" },
    { to: "/suggestions", label: "Feedback", icon: Chat, testid: "nav-suggestions" },
    { to: "/pricing", label: "Plans", icon: CreditCard, testid: "nav-plans" },
  ];
}

export default function GlobalNav() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    setOpen(false);
    navigate("/");
  };

  const links = navForUser(user);

  return (
    <header className="sticky top-0 z-40 bg-paper/95 backdrop-blur border-b-2 border-ink">
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between gap-3">
        <Link to={user ? "/dashboard" : "/"} className="flex items-center gap-2 shrink-0" data-testid="globalnav-brand">
          <div className="border-2 border-ink rounded-md bg-mint p-1.5 shadow-brutal">
            <GraduationCap size={20} weight="duotone" />
          </div>
          <span className="font-display font-black text-xl tracking-tight">Learnify</span>
        </Link>

        <nav className="hidden lg:flex items-center gap-1 flex-wrap" data-testid="globalnav-desktop">
          {links.map((l) => (
            <NavLink
              key={l.to} to={l.to} end={l.end}
              data-testid={l.testid}
              className={({ isActive }) =>
                `inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border-2 text-sm font-bold transition-all duration-150 whitespace-nowrap ${
                  isActive ? "border-ink bg-butter shadow-brutal" : "border-transparent hover:border-ink hover:bg-mint"
                }`
              }
            >
              <l.icon size={14} weight="bold" />
              <span>{l.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-2 shrink-0">
          <AccessibilityMenu />
          {user ? (
            <div className="hidden lg:flex items-center gap-2">
              <span className="inline-flex items-center gap-2 border-2 border-ink rounded-md bg-white px-2 py-1.5 shadow-brutal">
                {user.picture ? (
                  <img src={user.picture} alt="" className="w-6 h-6 rounded-full border border-ink" />
                ) : (
                  <span className="w-6 h-6 rounded-full bg-peach border border-ink flex items-center justify-center text-xs font-bold">
                    {user.name?.[0]?.toUpperCase() || "U"}
                  </span>
                )}
                <span className="text-sm font-bold">{user.name?.split(" ")[0] || "Me"}</span>
              </span>
              <button onClick={handleLogout} data-testid="globalnav-logout"
                className="brutal-btn bg-white hover:bg-peach text-sm inline-flex items-center gap-1.5 py-1.5 px-2.5">
                <SignOut size={14} weight="bold" /> Sign out
              </button>
            </div>
          ) : (
            <div className="hidden md:flex items-center gap-2">
              <Link to="/login" className="brutal-btn bg-white hover:bg-butter text-sm py-2 px-3 inline-flex items-center gap-1.5" data-testid="globalnav-login">
                <SignIn size={14} weight="bold" /> Sign in
              </Link>
              <Link to="/register" className="brutal-btn bg-ink text-white text-sm py-2 px-3" data-testid="globalnav-register">
                Get started
              </Link>
            </div>
          )}

          <button data-testid="globalnav-mobile-toggle" onClick={() => setOpen(!open)}
            className="lg:hidden border-2 border-ink rounded-md p-2 bg-butter shadow-brutal" aria-label="Menu">
            {open ? <X size={18} /> : <List size={18} />}
          </button>
        </div>
      </div>

      {open && (
        <div className="lg:hidden border-t-2 border-ink bg-white" data-testid="globalnav-mobile-menu">
          <div className="max-w-7xl mx-auto px-4 py-3 grid grid-cols-2 gap-2">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.end} onClick={() => setOpen(false)} data-testid={`${l.testid}-m`}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2 rounded-md border-2 font-bold text-sm ${isActive ? "border-ink bg-butter shadow-brutal" : "border-ink/30 bg-white"}`
                }>
                <l.icon size={16} weight="bold" /> {l.label}
              </NavLink>
            ))}
            {user ? (
              <button onClick={handleLogout} data-testid="globalnav-logout-m"
                className="flex items-center gap-2 px-3 py-2 rounded-md border-2 border-ink bg-peach font-bold text-sm col-span-2">
                <SignOut size={16} weight="bold" /> Sign out
              </button>
            ) : (
              <div className="col-span-2 grid grid-cols-2 gap-2">
                <Link to="/login" onClick={() => setOpen(false)} className="brutal-btn bg-white text-sm" data-testid="globalnav-login-m">Sign in</Link>
                <Link to="/register" onClick={() => setOpen(false)} className="brutal-btn bg-ink text-white text-sm" data-testid="globalnav-register-m">Get started</Link>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
