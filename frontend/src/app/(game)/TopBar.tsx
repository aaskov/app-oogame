"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/useAuth";
import { usePlanets } from "@/hooks/usePlanets";
import type { api } from "@/lib/api";

export function TopBar({ client }: { client?: typeof api }) {
  const { logout } = useAuth();
  const { planets } = usePlanets(client);
  const { id } = useParams<{ id?: string }>();
  const planetName = id ? planets.find((planet) => planet.id === id)?.name : undefined;

  return (
    <header className="flex min-h-14 items-center justify-between gap-3 border-b border-border bg-surface px-4 text-foreground">
      <Link href="/homeworld" className="flex min-h-11 items-center text-base font-semibold">
        {planetName ?? "OOGame"}
      </Link>
      <Button variant="secondary" onClick={logout}>
        Log out
      </Button>
    </header>
  );
}
