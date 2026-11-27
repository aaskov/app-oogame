"use client";

import { useEffect, useState } from "react";

import { api as defaultApi, type GalaxySystem } from "@/lib/api";

type Api = typeof defaultApi;

function keyOf(galaxy: number, system: number) {
  return `${galaxy}:${system}`;
}

export function useGalaxy(galaxy: number, system: number, client: Api = defaultApi) {
  const [data, setData] = useState<GalaxySystem | null>(null);
  const [error, setError] = useState<number | null>(null);
  const [loadedKey, setLoadedKey] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    client
      .GET("/galaxy/{galaxy}/{system}", { params: { path: { galaxy, system } } })
      .then(({ data, response }) => {
        if (cancelled) return;
        if (data) {
          setData(data);
          setError(null);
        } else {
          setData(null);
          setError(response.status);
        }
        setLoadedKey(keyOf(galaxy, system));
      })
      .catch(() => {
        if (!cancelled) {
          setData(null);
          setError(0);
          setLoadedKey(keyOf(galaxy, system));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [galaxy, system, client]);

  return { system: data, loading: keyOf(galaxy, system) !== loadedKey, error };
}
