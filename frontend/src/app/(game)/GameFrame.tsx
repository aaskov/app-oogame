"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/hooks/useAuth";
import { TopBar } from "./TopBar";

export function GameFrame({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  // `loading` is also true during the server render, before the session
  // check has resolved there. Treating that the same as logged-out would
  // mean the frame never reaches the static shell, so only hide it once the
  // check actually resolves to logged-out.
  if (!loading && !user) {
    return null;
  }

  return (
    <div className="flex flex-1 flex-col">
      <TopBar />
      {children}
    </div>
  );
}
