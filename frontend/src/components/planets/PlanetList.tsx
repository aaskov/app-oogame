"use client";

import type { Planet } from "@/lib/api";

export function PlanetList({
  planets,
  selectedId,
  onSelect,
}: {
  planets: Planet[];
  selectedId: string | null;
  onSelect: (planetId: string) => void;
}) {
  return (
    <ul aria-label="Planets" className="flex gap-2 overflow-x-auto sm:flex-col sm:overflow-visible">
      {planets.map((planet) => (
        <li key={planet.id}>
          <button
            type="button"
            onClick={() => onSelect(planet.id)}
            aria-pressed={planet.id === selectedId}
            className={`whitespace-nowrap rounded border px-3 py-2 text-sm font-medium ${
              planet.id === selectedId ? "border-zinc-900 bg-zinc-900 text-white" : "border-zinc-400"
            }`}
          >
            {planet.name}
          </button>
        </li>
      ))}
    </ul>
  );
}
