"use client";

import { useEffect, useRef, useState } from "react";

import { api as defaultApi, type Mine, type MineKind, type Vault } from "@/lib/api";

type Api = typeof defaultApi;

export type UpgradeResult = { status: number; mine?: Mine; vault?: Vault };

export function useMines(planetId: string | null, client: Api = defaultApi) {
  const [mines, setMines] = useState<Mine[]>([]);
  const [error, setError] = useState<number | null>(null);
  const [loadedPlanetId, setLoadedPlanetId] = useState<string | null>(null);
  const currentPlanetId = useRef(planetId);

  useEffect(() => {
    currentPlanetId.current = planetId;
  }, [planetId]);

  useEffect(() => {
    if (!planetId) {
      return;
    }
    let cancelled = false;
    client
      .GET("/planets/{planet_id}/mines", { params: { path: { planet_id: planetId } } })
      .then(({ data, response }) => {
        if (cancelled) return;
        if (data) {
          setMines(data);
          setError(null);
        } else {
          setMines([]);
          setError(response.status);
        }
        setLoadedPlanetId(planetId);
      })
      .catch(() => {
        if (!cancelled) {
          setMines([]);
          setError(0);
          setLoadedPlanetId(planetId);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [planetId, client]);

  async function upgrade(mine: MineKind): Promise<UpgradeResult> {
    if (!planetId) {
      return { status: 0 };
    }
    const requestedPlanetId = planetId;
    const { data, response } = await client.POST("/planets/{planet_id}/mines/{mine}/upgrade", {
      params: { path: { planet_id: planetId, mine } },
    });
    if (currentPlanetId.current !== requestedPlanetId) {
      return { status: 0 };
    }
    if (data) {
      setMines((prev) => prev.map((m) => (m.kind === mine ? data.mine : m)));
      return { status: response.status, mine: data.mine, vault: data.vault };
    }
    return { status: response.status };
  }

  const loading = planetId !== null && planetId !== loadedPlanetId;

  return { mines, loading, error, upgrade };
}
