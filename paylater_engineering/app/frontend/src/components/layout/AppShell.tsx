import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Activity, BarChart3, BookOpenCheck, BrainCircuit, BriefcaseBusiness, ChevronLeft, Gauge, LayoutDashboard, Menu, ShieldCheck, Users, X } from "lucide-react";
import { getSession } from "../../services/auth-service";
import { hasPermission, type Permission } from "../../app/permissions";

const navigation: Array<{ label: string; path: string; icon: typeof Gauge; permission: Permission }> = [
  { label: "Overview", path: "/", icon: LayoutDashboard, permission: "overview:read" },
  { label: "Borrowers", path: "/borrowers", icon: Users, permission: "borrowers:read" },
  { label: "Risk Intelligence", path: "/risk", icon: BrainCircuit, permission: "risk:read" },
  { label: "Decisions", path: "/decisions", icon: ShieldCheck, permission: "decisions:read" },
  { label: "Portfolio", path: "/portfolio", icon: BarChart3, permission: "portfolio:read" },
  { label: "Models", path: "/models", icon: Gauge, permission: "models:read" },
  { label: "Monitoring", path: "/monitoring", icon: Activity, permission: "monitoring:read" },
  { label: "Audit & Governance", path: "/audit", icon: BookOpenCheck, permission: "audit:read" },
];

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const session = getSession();
  const location = useLocation();
  const current = navigation.find((item) => item.path === location.pathname);
  const visibleNavigation = navigation.filter((item) => hasPermission(session.role, item.permission));

  return (
    <div className="app-shell">
      <aside className={`sidebar ${collapsed ? "sidebar-collapsed" : ""} ${mobileOpen ? "sidebar-mobile-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><BriefcaseBusiness size={19} /></div>
          {!collapsed && <div><strong>PayLater</strong><span>Intelligence</span></div>}
          <button className="icon-button mobile-only" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X size={18} /></button>
        </div>
        <nav className="nav-list" aria-label="Primary navigation">
          {visibleNavigation.map(({ label, path, icon: Icon }) => (
            <NavLink key={path} to={path} end={path === "/"} className={({ isActive }) => `nav-link ${isActive ? "nav-link-active" : ""}`} onClick={() => setMobileOpen(false)}>
              <Icon size={18} /><span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <button className="collapse-button desktop-only" onClick={() => setCollapsed((value) => !value)} aria-label="Toggle sidebar">
          <ChevronLeft size={17} className={collapsed ? "rotate-180" : ""} /><span>{!collapsed && "Collapse menu"}</span>
        </button>
      </aside>
      {mobileOpen && <button className="sidebar-backdrop mobile-only" onClick={() => setMobileOpen(false)} aria-label="Close navigation" />}
      <main className="main-shell">
        <header className="topbar">
          <div className="topbar-title"><button className="icon-button mobile-only" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={20} /></button><div><span className="eyebrow">PayLater Intelligence</span><h1>{current?.label ?? "Overview"}</h1></div></div>
          <div className="topbar-actions"><span className="environment-badge"><span className="status-dot" />Connected environment</span><div className="profile"><div className="avatar">AU</div><div><strong>{session.displayName}</strong><span>{session.role}</span></div></div></div>
        </header>
        <div className="content"><Outlet /></div>
      </main>
    </div>
  );
}
