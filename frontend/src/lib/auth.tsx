import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useMemo, type ReactNode } from "react";
import { api, ApiError } from "./api";
import type { Permission, SessionInfo } from "./types";

interface AuthState {
  session: SessionInfo | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<SessionInfo>;
  logout: () => Promise<void>;
  can: (...perms: Permission[]) => boolean;
}

const AuthContext = createContext<AuthState | null>(null);

export const SESSION_KEY = ["session"] as const;

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: SESSION_KEY,
    queryFn: async () => {
      try {
        return await api.get<SessionInfo>("/auth/me");
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }
    },
    staleTime: 5 * 60_000,
    retry: false,
  });

  const login = useCallback(
    async (email: string, password: string) => {
      const s = await api.post<SessionInfo>("/auth/login", { email, password });
      qc.clear();
      qc.setQueryData(SESSION_KEY, s);
      return s;
    },
    [qc],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } finally {
      qc.clear();
      qc.setQueryData(SESSION_KEY, null);
    }
  }, [qc]);

  const value = useMemo<AuthState>(() => {
    const perms = new Set(data?.permissions ?? []);
    return {
      session: data ?? null,
      loading: isLoading,
      login,
      logout,
      can: (...p) => p.every((x) => perms.has(x)),
    };
  }, [data, isLoading, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
