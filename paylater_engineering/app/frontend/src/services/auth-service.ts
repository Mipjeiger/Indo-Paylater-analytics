import { useEffect, useState } from "react";
import type { Role } from "../app/permissions";

export type Session = {
  role: Role;
  displayName: string;
};

const STORAGE_KEY = "paylater_session_role";

export function getSession(): Session {
  if (typeof window !== "undefined") {
    const saved = localStorage.getItem(STORAGE_KEY) as Role | null;
    if (saved && ["Executive", "Risk Manager", "Risk Analyst", "Auditor", "Platform Administrator"].includes(saved)) {
      return { role: saved, displayName: `Authorized (${saved})` };
    }
  }
  return { role: "Risk Manager", displayName: "Authorized user" };
}

export function setSessionRole(role: Role) {
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY, role);
    window.dispatchEvent(new Event("paylater_role_change"));
  }
}

export function useSession(): [Session, (role: Role) => void] {
  const [session, setSession] = useState<Session>(getSession());

  useEffect(() => {
    const handleRoleChange = () => setSession(getSession());
    window.addEventListener("paylater_role_change", handleRoleChange);
    return () => window.removeEventListener("paylater_role_change", handleRoleChange);
  }, []);

  return [session, setSessionRole];
}
