import { useEffect, useState } from "react";
import { NavLink, Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { displayHandle, displayInitial } from "@/lib/displayName";
import { api } from "@/lib/api";
import { findSubject } from "@/lib/subjects";
import { NAV_SECTIONS, sectionVisible } from "@/lib/navSections";
import AccessibilityMenu from "@/components/AccessibilityMenu";
import {
  House, CalendarBlank, BookOpen, ClipboardText, Exam,
  Target, ChartLineUp, FileText, Megaphone, Robot, Crown, Bank, Compass,
  CaretDown, CaretRight, X, SignOut, Gear, List,
  ChalkboardTeacher, Chat, Trophy, CreditCard, Users, ShieldCheck, GraduationCap,
} from "@phosphor-icons/react";

const FALLBACK_CLASSES = [
  { id: "mathematics", name: "Maths" },
  { id: "english", name: "English" },
  { id: "biology", name: "Science" },
];

const COLLAPSE_KEY = "learnify_nav_collapsed";

function readCollapsed() {
  try { return JSON.parse(localStorage.getItem(COLLAPSE_KEY) || "{}"); } catch { return {}; }
}

// Build the pinned Home item + the four role-aware sections.
function buildNav({ user, classes }) {
  const isStaff = user?.role === "school_admin" || user?.role === "teacher" || user?.role === "owner";
  const isOwner = user?.role === "owner";

  const home = { to: isOwner ? "/dashboard" : (user?.role === "parent" ? "/parent" : "/dashboard"), label: "Home", icon: House, testid: "sn-home", end: true };

  if (user?.role === "parent") {
    return {
      home,
      sections: [
        {
          key: "account",
          items: [
            { to: "/parent", label: "Parent portal", icon: Users, testid: "sn-parent" },
            { to: "/life-skills", label: "Life Skills", icon: GraduationCap, testid: "sn-life-skills" },
            { to: "/suggestions", label: "Feedback", icon: Chat, testid: "sn-suggestions" },
          ],
        },
      ],
    };
  }

  const learn = [
    { to: "/timetable", label: "Timetable", icon: CalendarBlank, testid: "sn-timetable" },
    {
      to: "/subjects", label: "Classes", icon: BookOpen, testid: "sn-classes",
      children: classes.map((c) => ({ to: `/subjects/${c.id}`, label: c.name, testid: `sn-class-${c.id}` })),
    },
    { to: "/homework", label: "Homework", icon: ClipboardText, testid: "sn-homework" },
    { to: "/assessments", label: "Assessments", icon: Exam, testid: "sn-assessments" },
    { to: "/practice", label: "Practice", icon: Target, testid: "sn-practice" },
    { to: "/progress", label: "Progress", icon: ChartLineUp, testid: "sn-progress" },
    { to: "/reports", label: "Reports", icon: FileText, testid: "sn-reports" },
    { to: "/announcements", label: "Announcements", icon: Megaphone, testid: "sn-announcements" },
    { to: "/help", label: "AI Tutor Support", icon: Robot, testid: "sn-ai-support" },
  ];

  const teach = [];
  if (isStaff) {
    teach.push({ to: "/teacher", label: "Teach", icon: ChalkboardTeacher, testid: "sn-teacher" });
    teach.push({ to: "/classes", label: "Roster", icon: Users, testid: "sn-roster" });
    teach.push({ to: "/parent-requests", label: "Parent access", icon: Users, testid: "sn-parent-requests" });
  }

  const school = [];
  if (isOwner) {
    school.push({ to: "/owner", label: "Owner HQ", icon: Crown, testid: "sn-owner" });
    school.push({ to: "/compliance", label: "Compliance", icon: ShieldCheck, testid: "sn-compliance" });
    school.push({ to: "/owner/payouts", label: "Payouts", icon: Bank, testid: "sn-payouts" });
  }

  const account = [];
  if (user?.role === "student") {
    account.push({ to: "/my-record", label: "My record", icon: Trophy, testid: "sn-myrecord" });
  }
  if (isOwner) {
    account.push({ to: "/parent", label: "Parent portal", icon: Users, testid: "sn-parent" });
  }
  account.push({ to: "/dreams", label: "Dreams", icon: Compass, testid: "sn-dreams" });
  account.push({ to: "/suggestions", label: "Feedback", icon: Chat, testid: "sn-suggestions" });
  account.push({ to: "/pricing", label: "Plans", icon: CreditCard, testid: "sn-plans" });
  account.push({ to: "/settings", label: "Settings", icon: Gear, testid: "sn-settings" });

  const sections = [
    { key: "learn", items: learn },
    { key: "teach", items: teach },
    { key: "school", items: school },
    { key: "account", items: account },
  ].filter((s) => s.items.length > 0);

  return { home, sections };
}

function NavItem({ item, onNavigate }) {
  const location = useLocation();
  const Icon = item.icon;
  const [expanded, setExpanded] = useState(() => {
    const c = readCollapsed();
    return c[`item:${item.testid}`] !== undefined ? !c[`item:${item.testid}`] : true;
  });
  const hasChildren = item.children && item.children.length > 0;
  const activeParent =
    hasChildren && (location.pathname === item.to || location.pathname.startsWith(item.to + "/"));

  const toggle = () => {
    setExpanded((v) => {
      const next = !v;
      const c = readCollapsed();
      c[`item:${item.testid}`] = !next;
      localStorage.setItem(COLLAPSE_KEY, JSON.stringify(c));
      return next;
    });
  };

  return (
    <li>
      <div className="flex items-center gap-1">
        <NavLink
          to={item.to}
          end={item.end}
          onClick={onNavigate}
          data-testid={item.testid}
          className={({ isActive }) =>
            `flex-1 flex items-center gap-3 px-3 py-2 rounded-md text-sm font-bold border-2 transition-all duration-150
             ${isActive || activeParent
               ? "bg-butter border-ink shadow-brutal"
               : "text-ink border-transparent hover:bg-mint hover:border-ink"}`
          }
        >
          <Icon size={18} weight="bold" />
          <span className="flex-1">{item.label}</span>
        </NavLink>
        {hasChildren && (
          <button
            type="button"
            onClick={toggle}
            data-testid={`${item.testid}-toggle`}
            className="p-1.5 rounded-md border-2 border-transparent hover:border-ink text-ink"
            aria-label={expanded ? "Collapse" : "Expand"}
          >
            {expanded ? <CaretDown size={14} weight="bold" /> : <CaretRight size={14} weight="bold" />}
          </button>
        )}
      </div>
      {hasChildren && expanded && (
        <ul className="mt-1 ml-5 border-l-2 border-ink/20 pl-3 space-y-1">
          {item.children.map((c) => (
            <li key={c.to}>
              <NavLink
                to={c.to}
                onClick={onNavigate}
                data-testid={c.testid}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-bold transition-colors
                   ${isActive ? "bg-lavender text-ink" : "text-[#4A4A4A] hover:text-ink hover:bg-mint"}`
                }
              >
                <span className="w-1.5 h-1.5 rounded-full bg-ink/60" />
                {c.label}
              </NavLink>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

function Section({ section, label, onNavigate }) {
  const [open, setOpen] = useState(() => {
    const c = readCollapsed();
    return c[section.key] !== true; // default expanded
  });

  const toggle = () => {
    setOpen((v) => {
      const next = !v;
      const c = readCollapsed();
      c[section.key] = !next;
      localStorage.setItem(COLLAPSE_KEY, JSON.stringify(c));
      return next;
    });
  };

  return (
    <div className="pt-2">
      <button
        type="button"
        onClick={toggle}
        data-testid={`sn-section-${section.key}`}
        className="w-full flex items-center justify-between px-3 py-1.5 text-xs tracking-[0.2em] uppercase font-bold text-[#4A4A4A] hover:text-ink"
      >
        <span>{label}</span>
        {open ? <CaretDown size={12} weight="bold" /> : <CaretRight size={12} weight="bold" />}
      </button>
      {open && (
        <ul className="space-y-1 mt-1" data-testid={`sn-section-items-${section.key}`}>
          {section.items.map((item) => (
            <NavItem key={item.to + item.testid} item={item} onNavigate={onNavigate} />
          ))}
        </ul>
      )}
    </div>
  );
}

export default function SideNav({ mobileOpen, onMobileClose }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [classes, setClasses] = useState(FALLBACK_CLASSES);
  const [prefs, setPrefs] = useState({});
  const [schoolDefaults, setSchoolDefaults] = useState({});

  useEffect(() => {
    if (!user) return;
    const load = () => {
      api.get("/me/nav-prefs")
        .then(({ data }) => {
          setPrefs(data.prefs || {});
          setSchoolDefaults(data.school_defaults || {});
        })
        .catch(() => {});
    };
    load();
    window.addEventListener("nav-prefs-changed", load);
    return () => window.removeEventListener("nav-prefs-changed", load);
  }, [user]);

  useEffect(() => {
    if (!user) return;
    if (!user.school_id) { setClasses(FALLBACK_CLASSES); return; }
    api.get("/school/me").then(({ data }) => {
      const raw = data?.classes || [];
      const mapped = raw
        .map((c) => {
          const nameLower = (c.name || "").toLowerCase().trim();
          if (c.subject_id && findSubject(c.subject_id)) {
            return { id: c.subject_id, name: c.name || findSubject(c.subject_id).name };
          }
          if (findSubject(nameLower)) return { id: nameLower, name: c.name };
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

  const { home, sections } = buildNav({ user, classes });
  const sectionLabel = (key) => NAV_SECTIONS.find((s) => s.key === key)?.label || key;
  const visibleSections = sections.filter((s) => sectionVisible(s.key, prefs, schoolDefaults));

  return (
    <>
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-30 bg-ink/50" onClick={onMobileClose} aria-hidden />
      )}

      <aside
        data-testid="side-nav"
        className={`fixed lg:sticky top-0 left-0 z-40 h-screen w-64 bg-paper text-ink border-r-2 border-ink flex-shrink-0 flex flex-col
                    transform transition-transform lg:transform-none
                    ${mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}
      >
        <div className="flex items-center justify-between px-4 py-4 border-b-2 border-ink">
          <Link to={user.role === "parent" ? "/parent" : "/dashboard"} className="flex items-center gap-2" data-testid="side-nav-brand">
            <div className="bg-white rounded-md p-1 border-2 border-ink shadow-brutal">
              <img src="/learnify-mark-64.png" alt="Learnify" className="h-6 w-6 object-contain" data-testid="side-nav-logo" />
            </div>
            <span className="font-display font-black text-lg tracking-tight">Learnify</span>
          </Link>
          <div className="flex items-center gap-1">
            <div className="hidden lg:block"><AccessibilityMenu /></div>
            <button type="button" onClick={onMobileClose} className="lg:hidden text-ink" aria-label="Close menu">
              <X size={20} weight="bold" />
            </button>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-3">
          {/* Pinned Home — always visible so users are never stranded. */}
          <ul className="space-y-1">
            <NavItem item={home} onNavigate={onMobileClose} />
          </ul>
          {visibleSections.map((s) => (
            <Section key={s.key} section={s} label={sectionLabel(s.key)} onNavigate={onMobileClose} />
          ))}
        </nav>

        <div className="px-3 py-3 border-t-2 border-ink space-y-2">
          <div className="flex items-center gap-2 px-2 py-2 rounded-md bg-white border-2 border-ink">
            {user.picture ? (
              <img src={user.picture} alt="" className="w-8 h-8 rounded-full border-2 border-ink" />
            ) : (
              <div className="w-8 h-8 rounded-full bg-peach border-2 border-ink flex items-center justify-center text-sm font-bold">
                {displayInitial(user)}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <div className="text-xs font-bold truncate">{displayHandle(user)}</div>
              <div className="text-[10px] uppercase tracking-widest text-[#4A4A4A] truncate">{user.role}</div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Link
              to="/settings"
              onClick={onMobileClose}
              data-testid="side-nav-settings"
              className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-md text-sm font-bold bg-white border-2 border-ink hover:bg-butter transition-colors"
            >
              <Gear size={16} weight="bold" /> Settings
            </Link>
            <button
              type="button"
              onClick={handleLogout}
              data-testid="side-nav-logout"
              className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-md text-sm font-bold bg-peach border-2 border-ink hover:-translate-y-0.5 transition-transform"
            >
              <SignOut size={16} weight="bold" /> Sign out
            </button>
          </div>
          <div className="lg:hidden"><AccessibilityMenu /></div>
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
      <List size={18} weight="bold" />
    </button>
  );
}
