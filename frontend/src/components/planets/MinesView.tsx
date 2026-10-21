"use client";

import { useState } from "react";

import { useMines } from "@/hooks/useMines";
import type { Amounts } from "@/hooks/useVault";
import type { api, Mine, MineKind, Resources, Vault } from "@/lib/api";

const MINE_NAMES: Record<MineKind, string> = {
  metal_mine: "Metal mine",
  crystal_mine: "Crystal mine",
  deuterium_synthesizer: "Deuterium synthesizer",
};

function canAfford(amounts: Amounts | null, cost: Resources) {
  if (!amounts) {
    return false;
  }
  return (
    amounts.metal >= cost.metal && amounts.crystal >= cost.crystal && amounts.deuterium >= cost.deuterium
  );
}

export function MinesView({
  planetId,
  client,
  amounts,
  onUpgraded,
}: {
  planetId: string | null;
  client?: typeof api;
  amounts: Amounts | null;
  onUpgraded: (vault: Vault) => void;
}) {
  const { mines, loading, error, upgrade } = useMines(planetId, client);
  const [actionError, setActionError] = useState<number | null>(null);
  const [pending, setPending] = useState<MineKind | null>(null);
  const [actionPlanetId, setActionPlanetId] = useState(planetId);

  if (planetId !== actionPlanetId) {
    setActionPlanetId(planetId);
    setActionError(null);
    setPending(null);
  }

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

  async function handleUpgrade(mine: MineKind) {
    setPending(mine);
    setActionError(null);
    const result = await upgrade(mine);
    setPending(null);
    if (result.vault) {
      onUpgraded(result.vault);
    } else {
      setActionError(result.status);
    }
  }

  return (
    <section aria-label="Mines" className="flex flex-col gap-4">
      {actionError === 409 && (
        <p role="alert" className="text-sm text-red-600">
          Not enough resources.
        </p>
      )}
      {actionError === 404 && (
        <p role="alert" className="text-sm text-red-600">
          This planet was not found.
        </p>
      )}
      <ul className="flex flex-col gap-3">
        {mines.map((mine: Mine) => {
          const name = MINE_NAMES[mine.kind];
          const affordable = canAfford(amounts, mine.upgrade_cost);
          return (
            <li key={mine.kind} className="flex items-center justify-between gap-4 border-b border-zinc-200 pb-3">
              <div>
                <p className="font-medium">{name}</p>
                <p className="text-sm text-zinc-500">
                  Level {mine.level} · +{mine.production_per_hour.toLocaleString("en-US")}/h
                </p>
                <p className="text-sm text-zinc-500">
                  Cost: {mine.upgrade_cost.metal.toLocaleString("en-US")} metal,{" "}
                  {mine.upgrade_cost.crystal.toLocaleString("en-US")} crystal
                </p>
              </div>
              <button
                type="button"
                aria-label={`Upgrade ${name}`}
                disabled={!affordable || pending === mine.kind}
                onClick={() => handleUpgrade(mine.kind)}
                className="rounded border border-zinc-900 px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:border-zinc-300 disabled:text-zinc-300"
              >
                Upgrade
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
