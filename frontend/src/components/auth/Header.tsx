"use client";

import Link from "next/link";

import { useAuth } from "@/hooks/useAuth";

export function Header() {
  const { user, loading, logout } = useAuth();

  return (
    <header className="flex flex-wrap items-center justify-end gap-3 border-b border-border bg-surface px-4 py-3 text-sm text-foreground">
      {loading ? null : user ? (
        <>
          <Link href="/homeworld" className="flex min-h-11 items-center underline">
            Planets
          </Link>
          <span>{user.email}</span>
          <button
            type="button"
            onClick={logout}
            className="flex min-h-11 items-center rounded border border-border px-3 py-1"
          >
            Log out
          </button>
        </>
      ) : (
        <>
          <Link href="/login" className="flex min-h-11 items-center underline">
            Log in
          </Link>
          <Link href="/register" className="flex min-h-11 items-center underline">
            Register
          </Link>
        </>
      )}
    </header>
  );
}
