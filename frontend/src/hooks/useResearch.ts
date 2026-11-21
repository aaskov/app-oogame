"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api as defaultApi, type Research, type TechKind, type Vault } from "@/lib/api";

type Api = typeof defaultApi;

export type StartResult = { status: number; research?: Research; vault?: Vault; detail?: string };

export function useResearch(client: Api = defaultApi) {
  const [research, setResearch] = useState<Research | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<number | null>(null);
  const latestReload = useRef(0);

  useEffect(() => {
    let cancelled = false;
    client
      .GET("/research")
      .then(({ data, response }) => {
        if (cancelled) return;
        if (data) {
          setResearch(data);
          setError(null);
        } else {
          setResearch(null);
          setError(response.status);
        }
        setLoading(false);
      })
      .catch(() => {
        if (!cancelled) {
          setResearch(null);
          setError(0);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [client]);

  // Used to pick up the research that completes on read (docs/adr/0117) once
  // a countdown reaches 0, and after a reload call from outside this hook.
  const reload = useCallback(async () => {
    const reloadId = ++latestReload.current;
    try {
      const { data, response } = await client.GET("/research");
      if (reloadId !== latestReload.current) {
        return;
      }
      if (data) {
        setResearch(data);
        setError(null);
      } else {
        setError(response.status);
      }
    } catch {
      // The research from before stays on screen.
    }
  }, [client]);

  async function start(planetId: string, kind: TechKind): Promise<StartResult> {
    const { data, error, response } = await client.POST("/planets/{planet_id}/research/{kind}/start", {
      params: { path: { planet_id: planetId, kind } },
    });
    if (!data) {
      return { status: response.status, detail: error?.detail };
    }
    setResearch(data.research);
    return { status: response.status, research: data.research, vault: data.vault };
  }

  return { research, loading, error, start, reload };
}
