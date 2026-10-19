"use client";

import { useCallback, useEffect, useState } from "react";

import { api as defaultApi, type Vault, type VaultUpdate } from "@/lib/api";

type Api = typeof defaultApi;

export type VaultResult = { ok: true } | { ok: false; status: number };

export function useVault(planetId: string | null, client: Api = defaultApi) {
  const [vault, setVault] = useState<Vault | null>(null);
  const [error, setError] = useState<number | null>(null);
  const [loadedPlanetId, setLoadedPlanetId] = useState<string | null>(null);

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
          setError(null);
        } else {
          setVault(null);
          setError(response.status);
        }
        setLoadedPlanetId(planetId);
      })
      .catch(() => {
        if (!cancelled) {
          setVault(null);
          setError(0);
          setLoadedPlanetId(planetId);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [planetId, client]);

  const update = useCallback(
    async (values: VaultUpdate): Promise<VaultResult> => {
      if (!planetId) {
        return { ok: false, status: 0 };
      }
      try {
        const { data, response } = await client.PATCH("/planets/{planet_id}/vault", {
          params: { path: { planet_id: planetId } },
          body: values,
        });
        if (!data) {
          return { ok: false, status: response.status };
        }
        setVault(data);
        return { ok: true };
      } catch {
        return { ok: false, status: 0 };
      }
    },
    [planetId, client],
  );

  const loading = planetId !== null && planetId !== loadedPlanetId;

  return { vault, loading, error, update };
}
