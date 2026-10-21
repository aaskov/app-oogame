"use client";

import { useCallback, useEffect, useState } from "react";

import { api as defaultApi, type Vault } from "@/lib/api";

type Api = typeof defaultApi;

export type Amounts = { metal: number; crystal: number; deuterium: number };

function amountsAt(vault: Vault, now: number): Amounts {
  const hoursSinceCalculated = (now - Date.parse(vault.calculated_at)) / (1000 * 60 * 60);
  return {
    metal: Math.floor(vault.metal + vault.production_per_hour.metal * hoursSinceCalculated),
    crystal: Math.floor(vault.crystal + vault.production_per_hour.crystal * hoursSinceCalculated),
    deuterium: Math.floor(
      vault.deuterium + vault.production_per_hour.deuterium * hoursSinceCalculated,
    ),
  };
}

export function useVault(planetId: string | null, client: Api = defaultApi) {
  const [vault, setVaultState] = useState<Vault | null>(null);
  // 0, not Date.now(): reading the clock during render is unsafe under prerendering
  // (https://nextjs.org/docs/messages/blocking-prerender-current-time-client). The
  // real time is set from an effect (below) or from setVault, before vault is ever
  // non-null, so this initial value is never used to compute amounts.
  const [now, setNow] = useState(0);
  const [error, setError] = useState<number | null>(null);
  const [loadedPlanetId, setLoadedPlanetId] = useState<string | null>(null);

  const setVault = useCallback((next: Vault) => {
    setVaultState(next);
    setError(null);
    setNow(Date.now());
  }, []);

  useEffect(() => {
    if (!planetId) {
      return;
    }
    let cancelled = false;
    client
      .GET("/planets/{planet_id}/vault", { params: { path: { planet_id: planetId } } })
      .then(({ data, response }) => {
        if (cancelled) return;
        if (data) {
          setVault(data);
        } else {
          setVaultState(null);
          setError(response.status);
        }
        setLoadedPlanetId(planetId);
      })
      .catch(() => {
        if (!cancelled) {
          setVaultState(null);
          setError(0);
          setLoadedPlanetId(planetId);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [planetId, client, setVault]);

  useEffect(() => {
    if (!vault) {
      return;
    }
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [vault]);

  const loading = planetId !== null && planetId !== loadedPlanetId;
  const amounts = vault ? amountsAt(vault, now) : null;

  return { vault, amounts, loading, error, setVault };
}
