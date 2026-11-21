"use client";

import { useCallback, useState } from "react";

import { useCountdown } from "@/hooks/useCountdown";
import { usePlanets } from "@/hooks/usePlanets";
import { useResearch } from "@/hooks/useResearch";
import type { Amounts } from "@/hooks/useVault";
import type { api, Resources, TechKind, Vault } from "@/lib/api";

const TECH_NAMES: Record<TechKind, string> = {
  energy_technology: "Energy technology",
  plasma_technology: "Plasma technology",
};

function format(value: number) {
  return value.toLocaleString("en-US");
}

function canAfford(amounts: Amounts | null, cost: Resources) {
  if (!amounts) {
    return false;
  }
  return (
    amounts.metal >= cost.metal && amounts.crystal >= cost.crystal && amounts.deuterium >= cost.deuterium
  );
}

function costText(cost: Resources) {
  const parts = [`${format(cost.metal)} metal`, `${format(cost.crystal)} crystal`];
  if (cost.deuterium > 0) {
    parts.push(`${format(cost.deuterium)} deuterium`);
  }
  return `Cost: ${parts.join(", ")}`;
}

export function ResearchView({
  planetId,
  client,
  amounts,
  researchLabLevel,
  onStarted,
  onCountdownComplete,
}: {
  planetId: string | null;
  client?: typeof api;
  amounts: Amounts | null;
  researchLabLevel: number;
  onStarted: (vault: Vault) => void;
  onCountdownComplete: () => void;
}) {
  const { research, loading, start, reload } = useResearch(client);
  const { planets } = usePlanets(client);
  const [actionError, setActionError] = useState<{ status: number; detail?: string } | null>(null);
  const [pending, setPending] = useState<TechKind | null>(null);

  const running = research?.running;

  // The server completes a due research on the next read (docs/adr/0117), so
  // reading the research and the vault again is enough to show the result.
  const handleCountdownComplete = useCallback(() => {
    reload();
    onCountdownComplete();
  }, [reload, onCountdownComplete]);

  const countdownText = useCountdown(running?.finishes_at, handleCountdownComplete);

  if (!planetId || loading || !research) {
    return null;
  }

  async function handleStart(kind: TechKind) {
    if (!planetId) {
      return;
    }
    setPending(kind);
    setActionError(null);
    const result = await start(planetId, kind);
    setPending(null);
    if (result.vault) {
      onStarted(result.vault);
    } else {
      setActionError({ status: result.status, detail: result.detail });
    }
  }

  const runningPlanetName = running
    ? (planets.find((planet) => planet.id === running.planet_id)?.name ?? running.planet_id)
    : undefined;

  return (
    <section aria-label="Research" className="flex flex-col gap-4">
      {actionError?.status === 409 && (
        <p role="alert" className="text-sm text-danger">
          {actionError.detail}
        </p>
      )}
      {actionError?.status === 404 && (
        <p role="alert" className="text-sm text-danger">
          This planet was not found.
        </p>
      )}
      <ul className="flex flex-col gap-3">
        {research.technologies.map((technology) => {
          const name = TECH_NAMES[technology.kind];
          const affordable = canAfford(amounts, technology.cost);
          const isResearchingThis = technology.kind === running?.kind;
          const anotherResearchRuns = running !== undefined && !isResearchingThis;
          const label = !technology.available
            ? "Needs energy technology 1"
            : anotherResearchRuns
              ? "Another research runs"
              : "Start";
          return (
            <li
              key={technology.kind}
              className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-border pb-3"
            >
              <div className="min-w-0">
                <p className="font-medium">{name}</p>
                <p className="text-sm text-muted">Level {technology.level}</p>
                {isResearchingThis && countdownText && (
                  <p className="text-sm text-muted">
                    Researching on {runningPlanetName} · {countdownText}
                  </p>
                )}
                <p className="text-sm text-muted">{costText(technology.cost)}</p>
              </div>
              <button
                type="button"
                aria-label={`Start ${name}`}
                disabled={
                  !technology.available ||
                  running !== undefined ||
                  researchLabLevel === 0 ||
                  !affordable ||
                  pending === technology.kind
                }
                onClick={() => handleStart(technology.kind)}
                className="min-h-11 min-w-11 rounded border border-accent px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:border-border disabled:text-muted"
              >
                {label}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
