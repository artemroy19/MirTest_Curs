import type { UserRole } from "../store/sessionStore";

export function getDefaultRoute(role?: UserRole | null) {
  return role === "teacher" || role === "admin" ? "/teacher/tests" : "/tests";
}
