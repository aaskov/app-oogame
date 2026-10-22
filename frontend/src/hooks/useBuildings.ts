"use client";

import { useEffect, useRef, useState } from "react";

import { api as defaultApi, type Building, type BuildingKind, type Vault } from "@/lib/api";

type Api = typeof defaultApi;

export type UpgradeResult = { status: number; vault?: Vault };

export function useBuildings(planetId: string | null, client: Api = defaultApi) {
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [error, setError] = useState<number | null>(null);
  const [loadedPlanetId, setLoadedPlanetId] = useState<string | null>(null);
  const currentPlanetId = useRef(planetId);
  const latestReload = useRef(0);

  useEffect(() => {
    currentPlanetId.current = planetId;
  }, [planetId]);

  useEffect(() => {
    if (!planetId) {
      return;
    }
    let cancelled = false;
    client
      .GET("/planets/{planet_id}/buildings", { params: { path: { planet_id: planetId } } })
      .then(({ data, response }) => {
        if (cancelled) return;
        if (data) {
          setBuildings(data);
          setError(null);
        } else {
          setBuildings([]);
          setError(response.status);
        }
        setLoadedPlanetId(planetId);
      })
      .catch(() => {
        if (!cancelled) {
          setBuildings([]);
          setError(0);
          setLoadedPlanetId(planetId);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [planetId, client]);

  // An upgrade changes the energy factor, which changes the production of the
  // other mines, so the list is read again. A failed read keeps the old list.
  async function reload(requestedPlanetId: string) {
    const reloadId = ++latestReload.current;
    try {
      const { data } = await client.GET("/planets/{planet_id}/buildings", {
        params: { path: { planet_id: requestedPlanetId } },
      });
      if (data && reloadId === latestReload.current && currentPlanetId.current === requestedPlanetId) {
        setBuildings(data);
      }
    } catch {
      // The list from before the upgrade stays on screen.
    }
  }

  async function upgrade(kind: BuildingKind): Promise<UpgradeResult> {
    if (!planetId) {
      return { status: 0 };
    }
    const requestedPlanetId = planetId;
    const { data, response } = await client.POST("/planets/{planet_id}/buildings/{kind}/upgrade", {
      params: { path: { planet_id: planetId, kind } },
    });
    if (currentPlanetId.current !== requestedPlanetId) {
      return { status: 0 };
    }
    if (!data) {
      return { status: response.status };
    }
    setBuildings((prev) => prev.map((b) => (b.kind === kind ? data.building : b)));
    reload(requestedPlanetId);
    return { status: response.status, vault: data.vault };
  }

  const loading = planetId !== null && planetId !== loadedPlanetId;

  return { buildings, loading, error, upgrade };
}
