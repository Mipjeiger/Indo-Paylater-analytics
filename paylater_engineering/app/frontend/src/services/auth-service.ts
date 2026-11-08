import type { Role } from "../app/permissions";

export type Session = {
  role: Role;
  displayName: string;
};

export function getSession(): Session {
  // Authentication is isolated until the backend auth contract is available.
  return { role: "Risk Manager", displayName: "Authorized user" };
}
