import { useEffect, useState } from "react";
import { NavLink, Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { displayHandle, displayInitial } from "@/lib/displayName";
import { api } from "@/lib/api";
import { findSubject } from "@/lib/subjects";
import AccessibilityMenu from "@/components/AccessibilityMenu";
import {
  House, CalendarBlank, BookOpen, ClipboardText, Exam,
  Target, ChartLineUp, FileText, Megaphone, Robot, Crown, Bank, Compass,
  CaretDown, CaretRight, Lock, GraduationCap, X, List, SignOut,
  ChalkboardTeacher, Chat, Trophy, CreditCard, Users
} from "@phosphor-icons/react";

const FALLBACK_CLASSES = [
  { id: "mathematics", name: "Maths" },
  { id: "english", name: "English" },
  { id: "biology", name: "Science" },
];

function buildNav({ user, classes }) {
  const isStaff = user?.role === "school_admin" || user?.role === "teacher" || user?.role === "owner";
  const isParent = user?.role === "parent";

  // Parents get a slim, focused nav — no student learning pages.
  if (isParent) {
    return [
      { to: "/dashboard", label: "Home", icon: House, testid: "sn-home", end: true },
      { to: "/parent", label: "Parent portal", icon: Users, testid: "sn-parent" },
      { to: "/suggestions", label: "Feedback", icon: Chat, testid: "sn-suggestions" },
    ];
  }

  const items = [
    { to: "/dashboard", label: "Home", icon: House, testid: "sn-home", end: true },
    { to: "/timetable", label: "Timetable", icon: CalendarBlank, testid: "sn-timetable" },
    {
      to: "/subjects", label: "Classes", icon: BookOpen, testid: "sn-classes",
      children: classes.map((c) => ({
        to: `/subjects/${c.id}`,
        label: c.name,
        testid: `sn-class-${c.id}`,
      })),
    },
    { to: "/homework", label: "Homework", icon: ClipboardText, testid: "sn-homework" },
    { to: "/assessments", label: "Assessments", icon: Exam, testid: "sn-assessments" },
    { to: "/practice", label: "Practice", icon: Target, testid: "sn-practice" },
    { to: "/progress", label: "Progress", icon: ChartLineUp, testid: "sn-progress" },
    { to: "/reports", label: "Reports", icon: FileText, testid: "sn-reports" },
    { to: "/announcements", label: "Announcements", icon: Megaphone, testid: "sn-announcements" },
    { to: "/help", label: "AI Tutor Support", icon: Robot, testid: "sn-ai-support" },
  ];

  if (isStaff) {
    items.push({ to: "/teacher", label: "Teach", icon: ChalkboardTeacher, testid: "sn-teacher" });
    items.push({ to: "/classes", label: "Roster", icon: Users, testid: "sn-roster" });
    items.push({ to: "/parent-requests", label: "Parent access", icon: Users, testid: "sn-parent-requests" });
  }
  if (user?.role === "student") {
    items.push({ to: "/my-record", label: "My record", icon: Trophy, testid: "sn-myrecord" });
  }
  if (user?.role === "owner") {
    items.push({ to: "/parent", label: "Parent portal", icon: Users, testid: "sn-parent" });
  }
  // Dreams for everyone — including owner — per user request
  items.push({ to: "/dreams", label: "Dreams", icon: Compass, testid: "sn-dreams" });
  items.push({ to: "/suggestions", label: "Feedback", icon: Chat, testid: "sn-suggestions" });
  items.push({ to: "/pricing", label: "Plans", icon: CreditCard, testid: "sn-plans" });

  if (user?.role === "owner") {
    items.unshift({ to: "/owner", label: "Owner HQ", icon: Crown, testid: "sn-owner" });
    items.push({ to: "/owner/payouts", label: "Payouts", icon: Bank, testid: "sn-payouts" });
  }
  return items;
}

function SideNavItem({ item, expanded, onToggle, onNavigate }) {
  const location = useLocation();
  const Icon = item.icon;
  const activeParent =
    item.children && item.children.length > 0 &&
    (location.pathname === item.to || location.pathname.startsWith(item.to + "/"));

  return (
    <li>
      <div className="flex items-center">
        <NavLink
          to={item.to}
          end={item.end}
          onClick={onNavigate}
          data-testid={item.testid}
          className={({ isActive }) =>
            `flex-1 flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
             ${isActive || activeParent
               ? "bg-indigo-600/25 text-indigo-200 border border-indigo-500/50"
               : "text-slate-300 hover:bg-slate-800/60 hover:text-white border border-transparent"}`
          }
        >
          <Icon size={18} weight="regular" />
          <span className="flex-1">{item.label}</span>
          {item.locked && <Lock size={14} className="text-slate-500" />}
        </NavLink>
        {item.children && item.children.length > 0 && (
          <button
            type="button"
            onClick={onToggle}
            data-testid={`${item.testid}-toggle`}
            className="ml-1 p-1 text-slate-400 hover:text-white"
            aria-label={expanded ? "Collapse" : "Expand"}
          >
            {expanded ? <CaretDown size={14} /> : <CaretRight size={14} />}
          </button>
        )}
      </div>
      {item.children && item.children.length > 0 && expanded && (
        <ul className="mt-1 ml-6 border-l border-slate-800 pl-3 space-y-1">
          {item.children.map((c) => (
            <li key={c.to}>
              <NavLink
                to={c.to}
                onClick={onNavigate}
                data-testid={c.testid}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium
                   ${isActive ? "bg-indigo-500/30 text-indigo-100" : "text-slate-400 hover:text-white hover:bg-slate-800/40"}`
                }
              >
                <span className="w-1.5 h-1.5 rounded-full bg-current opacity-70" />
                {c.label}
              </NavLink>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

export default function SideNav({ mobileOpen, onMobileClose }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [classes, setClasses] = useState(FALLBACK_CLASSES);
  const [expandedClasses, setExpandedClasses] = useState(true);

  useEffect(() => {
    if (!user) return;
    // Only fetch classes for school users; otherwise keep the curriculum-subject shortcuts.
    if (!user.school_id) {
      setClasses(FALLBACK_CLASSES);
      return;
    }
    api.get("/school/me").then(({ data }) => {
      const raw = data?.classes || [];
      const mapped = raw
        .map((c) => {
          const nameLower = (c.name || "").toLowerCase().trim();
          // 1. If the class explicitly names a curriculum subject, use its id
          if (c.subject_id && findSubject(c.subject_id)) {
            return { id: c.subject_id, name: c.name || findSubject(c.subject_id).name };
          }
          // 2. If the class NAME itself is a real curriculum subject, use it
          if (findSubject(nameLower)) {
            return { id: nameLower, name: c.name };
          }
          // 3. Otherwise the class (e.g. "7A") is a form group — surface as a link to the classes list
          //    rather than a dead /subjects/7a route.
          return null;
        })
        .filter(Boolean)
        .slice(0, 8);
      setClasses(mapped.length ? mapped : FALLBACK_CLASSES);
    }).catch(() => setClasses(FALLBACK_CLASSES));
  }, [user]);

  const handleLogout = async () => {
    await logout();
    onMobileClose?.();
    navigate("/");
  };

  if (!user) return null;

  const items = buildNav({ user, classes });

  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 z-30 bg-black/50"
          onClick={onMobileClose}
          aria-hidden
        />
      )}

      <aside
        data-testid="side-nav"
        className={`fixed lg:sticky top-0 left-0 z-40 h-screen w-64 bg-slate-950 text-white border-r border-slate-800 flex-shrink-0 flex flex-col
                    transform transition-transform lg:transform-none
                    ${mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}
      >
        <div className="flex items-center justify-between px-4 py-4 border-b border-slate-800">
          <Link to="/dashboard" className="flex items-center gap-2" data-testid="side-nav-brand">
            <div className="bg-white rounded-md p-1 shadow-brutal border border-white/40">
              <img
                src="/learnify-mark-64.png"
                alt="Learnify"
                className="h-6 w-6 object-contain"
                data-testid="side-nav-logo"
              />
            </div>
            <span className="font-display font-black text-lg tracking-tight">Learnify</span>
          </Link>
          <div className="flex items-center gap-1">
            <div className="hidden lg:block">
              <AccessibilityMenu />
            </div>
            <button
              type="button"
              onClick={onMobileClose}
              className="lg:hidden text-slate-400 hover:text-white"
              aria-label="Close menu"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4">
          <ul className="space-y-1">
            {items.map((item) => (
              <SideNavItem
                key={item.to}
                item={item}
                expanded={item.children && expandedClasses}
                onToggle={() => setExpandedClasses((v) => !v)}
                onNavigate={onMobileClose}
              />
            ))}
          </ul>
        </nav>

        <div className="px-3 py-3 border-t border-slate-800 space-y-2">
          <div className="flex items-center gap-2 px-2 py-2 rounded-lg bg-slate-900">
            {user.picture ? (
              <img src={user.picture} alt="" className="w-8 h-8 rounded-full" />
            ) : (
              <div className="w-8 h-8 rounded-full bg-indigo-500/30 flex items-center justify-center text-sm font-bold">
                {displayInitial(user)}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <div className="text-xs font-bold truncate">{displayHandle(user)}</div>
              <div className="text-[10px] uppercase tracking-widest text-slate-400 truncate">{user.role}</div>
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            data-testid="side-nav-logout"
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-bold bg-red-500/20 hover:bg-red-500/40 text-red-100 border border-red-500/40"
          >
            <SignOut size={16} weight="bold" /> Sign out
          </button>
          <div className="lg:hidden">
            <AccessibilityMenu />
          </div>
        </div>
      </aside>
    </>
  );
}

export function SideNavMobileTrigger({ onOpen }) {
  return (
    <button
      type="button"
      onClick={onOpen}
      data-testid="side-nav-mobile-open"
      className="lg:hidden border-2 border-ink rounded-md p-2 bg-white shadow-brutal"
      aria-label="Open menu"
    >
      <List size={18} />
    </button>
  );
}
