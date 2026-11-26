"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/useAuth";
import { usePlanets } from "@/hooks/usePlanets";
import type { api, Coordinates } from "@/lib/api";

function coordinatesText({ galaxy, system, position }: Coordinates) {
  return `[${galaxy}:${system}:${position}]`;
}

export function TopBar({ client }: { client?: typeof api }) {
  const { logout } = useAuth();
  const { planets } = usePlanets(client);
  const { id } = useParams<{ id?: string }>();
  const planet = id ? planets.find((planet) => planet.id === id) : undefined;
  const homePlanet = planets[0];

  return (
    <header className="flex min-h-14 items-center justify-between gap-3 border-b border-border bg-surface px-4 text-foreground">
      <div className="flex min-w-0 items-center gap-2">
        <Link href="/homeworld" className="flex min-h-11 items-center text-base font-semibold">
          {planet?.name ?? "OOGame"}
        </Link>
        {planet && (
          <span className="text-sm text-muted">{coordinatesText(planet.coordinates)}</span>
        )}
      </div>
      <div className="flex items-center gap-3">
        {homePlanet && (
          <Link
            href={`/galaxy/${homePlanet.coordinates.galaxy}/${homePlanet.coordinates.system}`}
            className="flex min-h-11 items-center px-2 text-sm font-medium"
          >
            Galaxy
          </Link>
        )}
        <Button variant="secondary" onClick={logout}>
          Log out
        </Button>
      </div>
    </header>
  );
}
