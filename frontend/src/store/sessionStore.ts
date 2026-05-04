import { create } from "zustand";
import { persist } from "zustand/middleware";

import { normalizeMediaUrl } from "../utils/media";

export type UserRole = "student" | "teacher" | "admin";

type SessionUser = {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  avatar?: string | null;
  role: UserRole;
};

type Tokens = {
  access: string;
  refresh: string;
};

type SessionState = {
  isAuthenticated: boolean;
  user: SessionUser | null;
  tokens: Tokens | null;
  setSession: (payload: { user: SessionUser; access: string; refresh: string }) => void;
  clearSession: () => void;
};

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      user: null,
      tokens: null,
      setSession: ({ user, access, refresh }) =>
        set({
          isAuthenticated: true,
          user: { ...user, avatar: normalizeMediaUrl(user.avatar) },
          tokens: { access, refresh }
        }),
      clearSession: () =>
        set({
          isAuthenticated: false,
          user: null,
          tokens: null
        })
    }),
    {
      name: "mirtest-session"
    }
  )
);
