"use client";

import Link from "next/link";

import { useAuth } from "@/hooks/useAuth";

export function Header() {
  const { user, loading, logout } = useAuth();

  return (
    <header className="flex flex-wrap items-center justify-end gap-3 border-b border-zinc-200 px-4 py-3 text-sm">
      {loading ? null : user ? (
        <>
          <span>{user.email}</span>
          <button type="button" onClick={logout} className="rounded border border-zinc-400 px-3 py-1">
            Log out
          </button>
        </>
      ) : (
        <>
          <Link href="/login" className="underline">
            Log in
          </Link>
          <Link href="/register" className="underline">
            Register
          </Link>
        </>
      )}
    </header>
  );
}
