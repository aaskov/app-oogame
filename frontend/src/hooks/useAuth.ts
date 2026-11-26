"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { api as defaultApi, type Credentials, type Registration, type User } from "@/lib/api";

type Api = typeof defaultApi;

export type AuthResult = { ok: true } | { ok: false; status: number; detail?: string };

export type Auth = {
  user: User | null;
  loading: boolean;
  login: (credentials: Credentials) => Promise<AuthResult>;
  register: (registration: Registration) => Promise<AuthResult>;
  logout: () => Promise<void>;
};

export const AuthContext = createContext<Auth | null>(null);

export function useAuthState(client: Api = defaultApi): Auth {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    client
      .GET("/auth/me")
      .then(({ data }) => data ?? null)
      .catch(() => null)
      .then((me) => {
        if (!cancelled) {
          setUser(me);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [client]);

  const login = useCallback(
    async (credentials: Credentials): Promise<AuthResult> => {
      try {
        const { data, response } = await client.POST("/auth/login", { body: credentials });
        if (!data) {
          return { ok: false, status: response.status };
        }
        setUser(data);
        return { ok: true };
      } catch {
        return { ok: false, status: 0 };
      }
    },
    [client],
  );

  const register = useCallback(
    async (registration: Registration): Promise<AuthResult> => {
      try {
        const { error, response } = await client.POST("/auth/register", { body: registration });
        if (!response.ok) {
          return { ok: false, status: response.status, detail: error?.detail };
        }
      } catch {
        return { ok: false, status: 0 };
      }
      return login({ email: registration.email, password: registration.password });
    },
    [client, login],
  );

  const logout = useCallback(async () => {
    try {
      const { response } = await client.POST("/auth/logout");
      if (response.ok) {
        setUser(null);
      }
    } catch {
      // The session is still valid on the server, so keep the user.
    }
  }, [client]);

  return { user, loading, login, register, logout };
}

export function useAuth(): Auth {
  const auth = useContext(AuthContext);
  if (!auth) {
    throw new Error("useAuth must be used inside an AuthProvider.");
  }
  return auth;
}
