export type Role = "Executive" | "Risk Manager" | "Risk Analyst" | "Auditor" | "Platform Administrator";

export type Permission =
  | "overview:read"
  | "borrowers:read"
  | "risk:read"
  | "risk:assess"
  | "decisions:read"
  | "decisions:write"
  | "portfolio:read"
  | "models:read"
  | "monitoring:read"
  | "audit:read";

const rolePermissions: Record<Role, Permission[]> = {
  Executive: [
    "overview:read",
    "borrowers:read",
    "decisions:read",
    "portfolio:read",
    "models:read",
  ],
  "Risk Manager": [
    "overview:read",
    "borrowers:read",
    "risk:read",
    "risk:assess",
    "decisions:read",
    "decisions:write",
    "portfolio:read",
    "models:read",
    "monitoring:read",
    "audit:read",
  ],
  "Risk Analyst": [
    "overview:read",
    "borrowers:read",
    "risk:read",
    "risk:assess",
    "decisions:read",
    "portfolio:read",
  ],
  Auditor: [
    "overview:read",
    "borrowers:read",
    "decisions:read",
    "portfolio:read",
    "models:read",
    "audit:read",
  ],
  "Platform Administrator": [
    "overview:read",
    "borrowers:read",
    "risk:read",
    "decisions:read",
    "portfolio:read",
    "models:read",
    "monitoring:read",
    "audit:read",
  ],
};

export function hasPermission(role: Role, permission: Permission): boolean {
  return rolePermissions[role]?.includes(permission) ?? false;
}
