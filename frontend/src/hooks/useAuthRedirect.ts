"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/hooks/useAuth";

// `/` and `/planets` go to `/homeworld` for a logged-in player, and to
// `/login` otherwise (docs/adr/0116).
export function useAuthRedirect() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) {
      return;
    }
    router.replace(user ? "/homeworld" : "/login");
  }, [loading, user, router]);
}
