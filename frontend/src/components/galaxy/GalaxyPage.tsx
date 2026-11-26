"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { useAuth } from "@/hooks/useAuth";
import { useGalaxy } from "@/hooks/useGalaxy";
import { usePlanets } from "@/hooks/usePlanets";
import type { api } from "@/lib/api";

function parseCoordinate(value: string | undefined): number | null {
  if (value === undefined || !/^[0-9]+$/.test(value)) {
    return null;
  }
  const parsed = Number(value);
  return parsed >= 1 ? parsed : null;
}

export function GalaxyPage({ client }: { client?: typeof api }) {
  const { galaxy: galaxyParam, system: systemParam } = useParams<{ galaxy: string; system: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const { planets } = usePlanets(client);
  const galaxy = parseCoordinate(galaxyParam);
  const system = parseCoordinate(systemParam);
  const valid = galaxy !== null && system !== null;
  const { system: data, loading, error } = useGalaxy(galaxy ?? 0, system ?? 0, client);

  if (loading) {
    return null;
  }

  if (!valid || error === 404) {
    const homePlanet = planets[0];
    const homeHref = homePlanet
      ? `/galaxy/${homePlanet.coordinates.galaxy}/${homePlanet.coordinates.system}`
      : "/homeworld";
    return (
      <main className="flex flex-1 flex-col gap-4 p-4">
        <p role="alert" className="text-sm text-danger">
          This system was not found.
        </p>
        <Link
          href={homeHref}
          className="flex min-h-11 w-fit items-center rounded border border-border px-4 text-sm font-medium"
        >
          Go to the home system
        </Link>
      </main>
    );
  }

  if (!data) {
    return null;
  }

  const atFirstSystem = data.system <= 1;
  const atLastSystem = data.system >= data.systems_per_galaxy;

  return (
    <main className="flex flex-1 flex-col gap-4 p-4">
      <h1 className="text-xl font-semibold">
        Galaxy [{data.galaxy}:{data.system}]
      </h1>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={atFirstSystem}
          onClick={() => router.push(`/galaxy/${data.galaxy}/${data.system - 1}`)}
          className="min-h-11 min-w-11 rounded border border-accent px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:border-border disabled:text-muted"
        >
          Previous system
        </button>
        <button
          type="button"
          disabled={atLastSystem}
          onClick={() => router.push(`/galaxy/${data.galaxy}/${data.system + 1}`)}
          className="min-h-11 min-w-11 rounded border border-accent px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:border-border disabled:text-muted"
        >
          Next system
        </button>
      </div>
      <ul aria-label="Positions" className="flex flex-col gap-2">
        {data.positions.map((position) => {
          const planet = position.planet;
          const isOwn = !!planet && !!user && planet.username === user.username;
          return (
            <li
              key={position.position}
              className="flex min-h-11 flex-wrap items-center justify-between gap-x-4 gap-y-1 rounded border border-border bg-surface px-4 py-3"
            >
              <span className="text-sm text-muted">
                [{data.galaxy}:{data.system}:{position.position}]
              </span>
              {planet ? (
                <span className="text-base font-medium">
                  {planet.name} · {planet.username}
                  {isOwn && <span className="text-accent"> (your planet)</span>}
                </span>
              ) : (
                <span className="text-base text-muted">Free</span>
              )}
            </li>
          );
        })}
      </ul>
    </main>
  );
}
