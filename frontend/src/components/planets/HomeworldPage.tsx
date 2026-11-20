"use client";

import Link from "next/link";

import { usePlanets } from "@/hooks/usePlanets";
import type { api } from "@/lib/api";

export function HomeworldPage({ client }: { client?: typeof api }) {
  const { planets, loading } = usePlanets(client);

  if (loading) {
    return null;
  }

  return (
    <main className="flex flex-1 flex-col gap-4 p-4">
      <h1 className="text-xl font-semibold">Planets</h1>
      <ul aria-label="Planets" className="flex flex-col gap-3">
        {planets.map((planet) => (
          <li key={planet.id}>
            <Link
              href={`/planets/${planet.id}/buildings`}
              className="flex min-h-11 items-center rounded border border-border bg-surface px-4 py-3 text-base font-medium"
            >
              {planet.name}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
