"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api as defaultApi, type Building, type BuildingKind, type Vault } from "@/lib/api";

type Api = typeof defaultApi;

export type UpgradeResult = { status: number; vault?: Vault; detail?: string };

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
  // Completion on read (docs/adr/0114) also means this call is how the
  // countdown reload picks up the finished building.
  const reloadList = useCallback(
    async (requestedPlanetId: string) => {
      const reloadId = ++latestReload.current;
      try {
        const { data } = await client.GET("/planets/{planet_id}/buildings", {
          params: { path: { planet_id: requestedPlanetId } },
        });
        if (data && reloadId === latestReload.current && currentPlanetId.current === requestedPlanetId) {
          setBuildings(data);
        }
      } catch {
        // The list from before stays on screen.
      }
    },
    [client],
  );

  const reload = useCallback(() => {
    if (!planetId) {
      return Promise.resolve();
    }
    return reloadList(planetId);
  }, [planetId, reloadList]);

  async function upgrade(kind: BuildingKind): Promise<UpgradeResult> {
    if (!planetId) {
      return { status: 0 };
    }
    const requestedPlanetId = planetId;
    const { data, error, response } = await client.POST("/planets/{planet_id}/buildings/{kind}/upgrade", {
      params: { path: { planet_id: planetId, kind } },
    });
    if (currentPlanetId.current !== requestedPlanetId) {
      return { status: 0 };
    }
    if (!data) {
      return { status: response.status, detail: error?.detail };
    }
    setBuildings((prev) => prev.map((b) => (b.kind === kind ? data.building : b)));
    reloadList(requestedPlanetId);
    return { status: response.status, vault: data.vault };
  }

  const loading = planetId !== null && planetId !== loadedPlanetId;

  return { buildings, loading, error, upgrade, reload };
}
