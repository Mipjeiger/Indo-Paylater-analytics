import { useState, useEffect } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Activity,
  BarChart3,
  BookOpenCheck,
  BrainCircuit,
  BriefcaseBusiness,
  Building2,
  ChevronLeft,
  Cpu,
  Gauge,
  LayoutDashboard,
  Menu,
  Search,
  ShieldCheck,
  Sliders,
  Users,
  X,
} from "lucide-react";
import { useSession } from "../../services/auth-service";
import { hasPermission, type Permission, type Role } from "../../app/permissions";

import type { LucideIcon } from "lucide-react";

type WorkspaceType = "business" | "engineering";

interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
  permission: Permission;
}

const businessNavigation: NavItem[] = [
  { label: "Executive Overview", path: "/", icon: LayoutDashboard, permission: "overview:read" },
  { label: "Borrowers Directory", path: "/borrowers", icon: Users, permission: "borrowers:read" },
  { label: "Risk Intelligence", path: "/risk", icon: BrainCircuit, permission: "risk:read" },
  { label: "Decision Management", path: "/decisions", icon: ShieldCheck, permission: "decisions:read" },
  { label: "Portfolio Analytics", path: "/portfolio", icon: BarChart3, permission: "portfolio:read" },
];

const engineeringNavigation: NavItem[] = [
  { label: "Model Registry", path: "/models", icon: Gauge, permission: "models:read" },
  { label: "Monitoring & Drift", path: "/monitoring", icon: Activity, permission: "monitoring:read" },
  { label: "Audit & Governance", path: "/audit", icon: BookOpenCheck, permission: "audit:read" },
];

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [session, setSessionRole] = useSession();
  const location = useLocation();
  const navigate = useNavigate();

  // Determine current workspace based on route
  const isEngineeringRoute = ["/models", "/monitoring", "/audit"].includes(location.pathname);
  const [workspace, setWorkspace] = useState<WorkspaceType>(isEngineeringRoute ? "engineering" : "business");

  // Keep workspace in sync with navigation
  useEffect(() => {
    if (["/models", "/monitoring", "/audit"].includes(location.pathname)) {
      setWorkspace("engineering");
    } else {
      setWorkspace("business");
    }
  }, [location.pathname]);

  const activeNav = workspace === "business" ? businessNavigation : engineeringNavigation;
  const visibleNav = activeNav.filter((item) => hasPermission(session.role, item.permission));
  const currentItem = [...businessNavigation, ...engineeringNavigation].find((item) => item.path === location.pathname);

  const handleWorkspaceChange = (nextWorkspace: WorkspaceType) => {
    setWorkspace(nextWorkspace);
    if (nextWorkspace === "business") {
      navigate("/");
    } else {
      navigate("/models");
    }
    setMobileOpen(false);
  };

  const rolesList: Role[] = [
    "Risk Manager",
    "Risk Analyst",
    "Executive",
    "Auditor",
    "Platform Administrator",
  ];

  return (
    <div className="app-shell">
      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside className={`sidebar ${collapsed ? "sidebar-collapsed" : ""} ${mobileOpen ? "sidebar-mobile-open" : ""}`}>
        {/* Brand */}
        <div className="brand">
          <div className="brand-mark">
            <BriefcaseBusiness size={18} />
          </div>
          {!collapsed && (
            <div className="brand-title">
              <strong>PayLater</strong>
              <span>Risk Intelligence</span>
            </div>
          )}
          <button className="btn-icon mobile-only" onClick={() => setMobileOpen(false)} aria-label="Close navigation" style={{ marginLeft: "auto" }}>
            <X size={16} />
          </button>
        </div>

        {/* Workspace Switcher */}
        {!collapsed && (
          <div className="workspace-switcher">
            <span className="workspace-switcher-label">Workspace</span>
            <div className="workspace-segmented">
              <button
                type="button"
                className={`workspace-btn ${workspace === "business" ? "workspace-btn-active" : ""}`}
                onClick={() => handleWorkspaceChange("business")}
              >
                <Building2 size={13} />
                <span>Business</span>
              </button>
              <button
                type="button"
                className={`workspace-btn ${workspace === "engineering" ? "workspace-btn-active" : ""}`}
                onClick={() => handleWorkspaceChange("engineering")}
              >
                <Cpu size={13} />
                <span>Engineering</span>
              </button>
            </div>
          </div>
        )}

        {/* Nav List */}
        <nav className="nav-section" aria-label="Workspace navigation">
          {visibleNav.map(({ label, path, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              end={path === "/"}
              className={({ isActive }) => `nav-link ${isActive ? "nav-link-active" : ""}`}
              onClick={() => setMobileOpen(false)}
            >
              <Icon size={17} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Sidebar Footer */}
        <div className="sidebar-footer">
          <button
            className="collapse-button desktop-only"
            onClick={() => setCollapsed((v) => !v)}
            aria-label="Toggle navigation"
          >
            <ChevronLeft size={16} style={{ transform: collapsed ? "rotate(180deg)" : "none", transition: "transform 0.2s" }} />
            <span>{!collapsed && "Collapse sidebar"}</span>
          </button>
        </div>
      </aside>

      {/* ── Main Workspace ───────────────────────────────────────────────── */}
      <div className="main-shell">
        {/* Topbar Header */}
        <header className="topbar">
          <div className="topbar-left">
            <button className="btn-icon mobile-only" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
              <Menu size={18} />
            </button>
            <div className="breadcrumbs">
              <span className="workspace-badge">
                {workspace === "business" ? "Business Intelligence" : "MLOps Platform"}
              </span>
              <span>/</span>
              <span className="breadcrumb-current">{currentItem?.label ?? "Overview"}</span>
            </div>
          </div>

          <div className="topbar-center">
            <div className="global-search">
              <Search size={14} style={{ color: "#94a3b8" }} />
              <input
                type="text"
                placeholder="Search borrower ID (e.g. ID_DEB_0001) or policy code…"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.target as HTMLInputElement).value) {
                    navigate(`/borrowers?q=${encodeURIComponent((e.target as HTMLInputElement).value)}`);
                  }
                }}
              />
              <kbd>↵</kbd>
            </div>
          </div>

          <div className="topbar-right">
            <div className="environment-pill">
              <span className="pulse-dot" />
              <span>Production Gateway</span>
            </div>

            <div className="role-selector" title="Switch active role to test RBAC rules">
              <Sliders size={13} style={{ color: "#64748b" }} />
              <select
                value={session.role}
                onChange={(e) => setSessionRole(e.target.value as Role)}
                aria-label="Simulate Role"
              >
                {rolesList.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </header>

        {/* Content View */}
        <main className="content-workspace">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
