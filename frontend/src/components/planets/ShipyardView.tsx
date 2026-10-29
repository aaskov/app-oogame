"use client";

import { useCallback, useState } from "react";

import { useCountdown } from "@/hooks/useCountdown";
import type { Amounts } from "@/hooks/useVault";
import { useShipyard } from "@/hooks/useShipyard";
import type { api, Resources, ShipKind, Vault } from "@/lib/api";

const SHIP_NAMES: Record<ShipKind, string> = {
  small_cargo: "Small cargo",
  light_fighter: "Light fighter",
};

function format(value: number) {
  return value.toLocaleString("en-US");
}

function totalCost(cost: Resources, count: number): Resources {
  return { metal: cost.metal * count, crystal: cost.crystal * count, deuterium: cost.deuterium * count };
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

function isValidCount(count: number) {
  return Number.isInteger(count) && count >= 1 && count <= 1000;
}

export function ShipyardView({
  planetId,
  client,
  amounts,
  shipyardLevel,
  onOrdered,
}: {
  planetId: string | null;
  client?: typeof api;
  amounts: Amounts | null;
  shipyardLevel: number;
  onOrdered: (vault: Vault) => void;
}) {
  const { shipyard, loading, error, order, reload } = useShipyard(planetId, client);
  const [counts, setCounts] = useState<Record<ShipKind, number>>({ small_cargo: 1, light_fighter: 1 });
  const [actionError, setActionError] = useState<{ status: number; detail?: string } | null>(null);
  const [pending, setPending] = useState<ShipKind | null>(null);
  const [actionPlanetId, setActionPlanetId] = useState(planetId);

  if (planetId !== actionPlanetId) {
    setActionPlanetId(planetId);
    setActionError(null);
    setPending(null);
  }

  const runningOrder = shipyard?.order;

  // The server completes due ships on the next read (docs/adr/0115), so
  // reading the shipyard again is enough to show the result.
  const handleOrderComplete = useCallback(() => {
    reload();
  }, [reload]);
  const noop = useCallback(() => {}, []);

  const nextCountdownText = useCountdown(runningOrder?.next_finishes_at, handleOrderComplete);
  const finishesCountdownText = useCountdown(runningOrder?.finishes_at, noop);

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

  if (!shipyard) {
    return null;
  }

  async function handleOrder(kind: ShipKind) {
    const count = counts[kind];
    setPending(kind);
    setActionError(null);
    const result = await order(kind, count);
    setPending(null);
    if (result.vault) {
      onOrdered(result.vault);
    } else {
      setActionError({ status: result.status, detail: result.detail });
    }
  }

  return (
    <section aria-label="Shipyard" className="flex flex-col gap-4">
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
        {shipyard.ships.map((ship) => {
          const name = SHIP_NAMES[ship.kind];
          const count = counts[ship.kind];
          const validCount = isValidCount(count);
          const affordable = validCount && canAfford(amounts, totalCost(ship.cost, count));
          const isOrderingThis = ship.kind === runningOrder?.kind;
          const anotherOrderRuns = runningOrder !== undefined && !isOrderingThis;
          return (
            <li
              key={ship.kind}
              className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-zinc-200 pb-3"
            >
              <div className="min-w-0">
                <p className="font-medium">{name}</p>
                <p className="text-sm text-zinc-500">
                  Built: {format(ship.count)} · {ship.build_seconds}s to build
                </p>
                {isOrderingThis && nextCountdownText && finishesCountdownText && (
                  <p className="text-sm text-zinc-500">
                    Building · {runningOrder.remaining} left · next {nextCountdownText} · all{" "}
                    {finishesCountdownText}
                  </p>
                )}
                <p className="text-sm text-zinc-500">{costText(ship.cost)}</p>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={1}
                  max={1000}
                  aria-label={`${name} count`}
                  value={count}
                  disabled={shipyardLevel === 0 || runningOrder !== undefined}
                  onChange={(e) =>
                    setCounts((prev) => ({ ...prev, [ship.kind]: Number(e.target.value) }))
                  }
                  className="w-20 rounded border border-zinc-300 px-2 py-1 text-sm disabled:text-zinc-300"
                />
                <button
                  type="button"
                  aria-label={`Order ${name}`}
                  disabled={
                    shipyardLevel === 0 ||
                    runningOrder !== undefined ||
                    !affordable ||
                    pending === ship.kind
                  }
                  onClick={() => handleOrder(ship.kind)}
                  className="rounded border border-zinc-900 px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:border-zinc-300 disabled:text-zinc-300"
                >
                  {anotherOrderRuns ? "Another order runs" : "Order"}
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
