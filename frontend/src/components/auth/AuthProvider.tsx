"use client";

import type { ReactNode } from "react";

import { AuthContext, useAuthState } from "@/hooks/useAuth";
import type { api } from "@/lib/api";

export function AuthProvider({
  api: client,
  children,
}: {
  api?: typeof api;
  children: ReactNode;
}) {
  return <AuthContext.Provider value={useAuthState(client)}>{children}</AuthContext.Provider>;
}
