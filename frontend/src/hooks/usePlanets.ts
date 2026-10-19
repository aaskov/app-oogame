"use client";

import { useEffect, useState } from "react";

import { api as defaultApi, type Planet } from "@/lib/api";

type Api = typeof defaultApi;

export function usePlanets(client: Api = defaultApi) {
  const [planets, setPlanets] = useState<Planet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    client
      .GET("/planets")
      .then(({ data, response }) => {
        if (cancelled) return;
        if (data) {
          setPlanets(data);
        } else {
          setError(response.status);
        }
        setLoading(false);
      })
      .catch(() => {
        if (!cancelled) {
          setError(0);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [client]);

  return { planets, loading, error };
}
