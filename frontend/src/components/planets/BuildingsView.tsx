"use client";

import { useCallback, useState } from "react";

import { useBuildings } from "@/hooks/useBuildings";
import { useCountdown } from "@/hooks/useCountdown";
import type { Amounts } from "@/hooks/useVault";
import type { api, Building, BuildingKind, Resources, Vault } from "@/lib/api";

const BUILDING_NAMES: Record<BuildingKind, string> = {
  metal_mine: "Metal mine",
  crystal_mine: "Crystal mine",
  deuterium_synthesizer: "Deuterium synthesizer",
  solar_plant: "Solar plant",
  metal_storage: "Metal storage",
  crystal_storage: "Crystal storage",
  deuterium_tank: "Deuterium tank",
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

function energyText({ produced, used }: Building["energy"]) {
  if (produced > 0) {
    return `+${format(produced)} energy`;
  }
  if (used > 0) {
    return `−${format(used)} energy`;
  }
  return "0 energy";
}

function costText(cost: Resources) {
  const parts = [`${format(cost.metal)} metal`, `${format(cost.crystal)} crystal`];
  if (cost.deuterium > 0) {
    parts.push(`${format(cost.deuterium)} deuterium`);
  }
  return `Cost: ${parts.join(", ")}`;
}

export function BuildingsView({
  planetId,
  client,
  amounts,
  onUpgraded,
  onCountdownComplete,
}: {
  planetId: string | null;
  client?: typeof api;
  amounts: Amounts | null;
  onUpgraded: (vault: Vault) => void;
  onCountdownComplete: () => void;
}) {
  const { buildings, loading, error, upgrade, reload } = useBuildings(planetId, client);
  const [actionError, setActionError] = useState<{ status: number; detail?: string } | null>(null);
  const [pending, setPending] = useState<BuildingKind | null>(null);
  const [actionPlanetId, setActionPlanetId] = useState(planetId);

  if (planetId !== actionPlanetId) {
    setActionPlanetId(planetId);
    setActionError(null);
    setPending(null);
  }

  const upgrading = buildings.find((building) => building.upgrade_finishes_at);

  // The server completes a due upgrade on the next read (docs/adr/0114), so
  // reading the list and the vault again is enough to show the result.
  const handleCountdownComplete = useCallback(() => {
    reload();
    onCountdownComplete();
  }, [reload, onCountdownComplete]);

  const countdownText = useCountdown(upgrading?.upgrade_finishes_at, handleCountdownComplete);

  if (!planetId || loading) {
    return null;
  }

  if (error === 404) {
    return (
      <p role="alert" className="text-sm text-red-600">
        This planet was not found.
      </p>
    );
  }

  async function handleUpgrade(kind: BuildingKind) {
    setPending(kind);
    setActionError(null);
    const result = await upgrade(kind);
    setPending(null);
    if (result.vault) {
      onUpgraded(result.vault);
    } else {
      setActionError({ status: result.status, detail: result.detail });
    }
  }

  return (
    <section aria-label="Buildings" className="flex flex-col gap-4">
      {actionError?.status === 409 && (
        <p role="alert" className="text-sm text-red-600">
          {actionError.detail}
        </p>
      )}
      {actionError?.status === 404 && (
        <p role="alert" className="text-sm text-red-600">
          This planet was not found.
        </p>
      )}
      <ul className="flex flex-col gap-3">
        {buildings.map((building) => {
          const name = BUILDING_NAMES[building.kind];
          const isStorage =
            building.kind === "metal_storage" ||
            building.kind === "crystal_storage" ||
            building.kind === "deuterium_tank";
          const isMine = !isStorage && building.kind !== "solar_plant";
          const affordable = canAfford(amounts, building.upgrade_cost);
          const isUpgradingThis = building.kind === upgrading?.kind;
          const anotherUpgradeRuns = upgrading !== undefined && !isUpgradingThis;
          return (
            <li
              key={building.kind}
              className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-zinc-200 pb-3"
            >
              <div className="min-w-0">
                <p className="font-medium">{name}</p>
                <p className="text-sm text-zinc-500">
                  {isMine
                    ? `Level ${building.level} · +${format(building.production_per_hour)}/h`
                    : `Level ${building.level}`}
                </p>
                {isUpgradingThis && countdownText && (
                  <p className="text-sm text-zinc-500">
                    Upgrading to level {building.level + 1} · {countdownText}
                  </p>
                )}
                {!isStorage && <p className="text-sm text-zinc-500">{energyText(building.energy)}</p>}
                <p className="text-sm text-zinc-500">{costText(building.upgrade_cost)}</p>
              </div>
              <button
                type="button"
                aria-label={`Upgrade ${name}`}
                disabled={upgrading !== undefined || !affordable || pending === building.kind}
                onClick={() => handleUpgrade(building.kind)}
                className="rounded border border-zinc-900 px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:border-zinc-300 disabled:text-zinc-300"
              >
                {anotherUpgradeRuns ? "Another upgrade runs" : "Upgrade"}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
