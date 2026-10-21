"use client";

import { useEffect, useState } from "react";

import { api as defaultApi, type Vault } from "@/lib/api";

type Api = typeof defaultApi;

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

  const loading = planetId !== null && planetId !== loadedPlanetId;

  return { vault, loading, error };
}
