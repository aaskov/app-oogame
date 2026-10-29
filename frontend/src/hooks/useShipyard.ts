"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api as defaultApi, type ShipKind, type Shipyard, type Vault } from "@/lib/api";

type Api = typeof defaultApi;

export type OrderResult = { status: number; shipyard?: Shipyard; vault?: Vault; detail?: string };

export function useShipyard(planetId: string | null, client: Api = defaultApi) {
  const [shipyard, setShipyard] = useState<Shipyard | null>(null);
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
      .GET("/planets/{planet_id}/ships", { params: { path: { planet_id: planetId } } })
      .then(({ data, response }) => {
        if (cancelled) return;
        if (data) {
          setShipyard(data);
          setError(null);
        } else {
          setShipyard(null);
          setError(response.status);
        }
        setLoadedPlanetId(planetId);
      })
      .catch(() => {
        if (!cancelled) {
          setShipyard(null);
          setError(0);
          setLoadedPlanetId(planetId);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [planetId, client]);

  // Used to pick up the ships that complete on read (docs/adr/0115) once a
  // countdown reaches 0, and after a reload call from outside this hook.
  const reloadShipyard = useCallback(
    async (requestedPlanetId: string) => {
      const reloadId = ++latestReload.current;
      try {
        const { data } = await client.GET("/planets/{planet_id}/ships", {
          params: { path: { planet_id: requestedPlanetId } },
        });
        if (data && reloadId === latestReload.current && currentPlanetId.current === requestedPlanetId) {
          setShipyard(data);
        }
      } catch {
        // The shipyard from before stays on screen.
      }
    },
    [client],
  );

  const reload = useCallback(() => {
    if (!planetId) {
      return Promise.resolve();
    }
    return reloadShipyard(planetId);
  }, [planetId, reloadShipyard]);

  async function order(kind: ShipKind, count: number): Promise<OrderResult> {
    if (!planetId) {
      return { status: 0 };
    }
    const requestedPlanetId = planetId;
    const { data, error, response } = await client.POST("/planets/{planet_id}/ships/{kind}/order", {
      params: { path: { planet_id: planetId, kind } },
      body: { count },
    });
    if (currentPlanetId.current !== requestedPlanetId) {
      return { status: 0 };
    }
    if (!data) {
      return { status: response.status, detail: error?.detail };
    }
    setShipyard(data.shipyard);
    return { status: response.status, shipyard: data.shipyard, vault: data.vault };
  }

  const loading = planetId !== null && planetId !== loadedPlanetId;

  return { shipyard, loading, error, order, reload };
}
