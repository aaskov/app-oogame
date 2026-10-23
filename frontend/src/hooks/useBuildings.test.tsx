import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useBuildings } from "@/hooks/useBuildings";
import { createApi } from "@/lib/api";

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(new Date("2026-10-19T00:00:00Z"));
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

const planetId = "b2b7b8d0-6e1a-4c9e-9b8a-9a9e3d9a1a01";

const metalMine = {
  kind: "metal_mine",
  level: 0,
  production_per_hour: 0,
  energy: { produced: 0, used: 0 },
  upgrade_cost: { metal: 60, crystal: 15, deuterium: 0 },
};
const solarPlant = {
  kind: "solar_plant",
  level: 0,
  production_per_hour: 0,
  energy: { produced: 0, used: 0 },
  upgrade_cost: { metal: 75, crystal: 30, deuterium: 0 },
};
const buildings = [metalMine, solarPlant];

const upgradedMetalMine = {
  ...metalMine,
  level: 1,
  production_per_hour: 33,
  energy: { produced: 0, used: 11 },
};
const upgraded = {
  building: upgradedMetalMine,
  vault: {
    planet_id: planetId,
    metal: 940,
    crystal: 985,
    deuterium: 0,
    production_per_hour: { metal: 63, crystal: 15, deuterium: 0 },
    energy: { produced: 0, used: 11 },
    calculated_at: "2026-10-19T00:05:00Z",
  },
};
const reloaded = [upgradedMetalMine, solarPlant];

type Reply = { status: number; body?: unknown };

function fakeFetch(routes: Record<string, Reply | Reply[]>, seen: Request[] = []) {
  return async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = new Request(input, init);
    seen.push(request);
    const entry = routes[`${request.method} ${new URL(request.url).pathname}`];
    if (!entry) {
      return new Response(null, { status: 404 });
    }
    const route = Array.isArray(entry) ? (entry.length > 1 ? entry.shift()! : entry[0]) : entry;
    return new Response(route.body === undefined ? null : JSON.stringify(route.body), {
      status: route.status,
      headers: { "Content-Type": "application/json" },
    });
  };
}

describe("useBuildings", () => {
  it("has no buildings when planetId is null", () => {
    const client = createApi(fakeFetch({}));
    const { result } = renderHook(() => useBuildings(null, client));

    expect(result.current.loading).toBe(false);
    expect(result.current.buildings).toEqual([]);
  });

  it("does not read the clock", async () => {
    const dateNow = vi.spyOn(Date, "now");
    const client = createApi(
      fakeFetch({ [`GET /planets/${planetId}/buildings`]: { status: 200, body: buildings } }),
    );
    const { result } = renderHook(() => useBuildings(planetId, client));
    expect(dateNow).not.toHaveBeenCalled();

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(dateNow).not.toHaveBeenCalled();
  });

  it("lists the buildings of the given planet", async () => {
    const seen: Request[] = [];
    const client = createApi(
      fakeFetch({ [`GET /planets/${planetId}/buildings`]: { status: 200, body: buildings } }, seen),
    );
    const { result } = renderHook(() => useBuildings(planetId, client));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.buildings).toEqual(buildings);
    expect(seen[0]?.url.endsWith(`/planets/${planetId}/buildings`)).toBe(true);
  });

  it("sets the error status on a 404", async () => {
    const client = createApi(
      fakeFetch({
        [`GET /planets/${planetId}/buildings`]: { status: 404, body: { detail: "Not found" } },
      }),
    );
    const { result } = renderHook(() => useBuildings(planetId, client));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.buildings).toEqual([]);
    expect(result.current.error).toBe(404);
  });

  it("upgrades a building, returns the vault, and reads the list again", async () => {
    const seen: Request[] = [];
    const client = createApi(
      fakeFetch(
        {
          [`GET /planets/${planetId}/buildings`]: [
            { status: 200, body: buildings },
            { status: 200, body: reloaded },
          ],
          [`POST /planets/${planetId}/buildings/metal_mine/upgrade`]: { status: 200, body: upgraded },
        },
        seen,
      ),
    );
    const { result } = renderHook(() => useBuildings(planetId, client));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome;
    await act(async () => {
      outcome = await result.current.upgrade("metal_mine");
    });

    expect(outcome).toEqual({ status: 200, vault: upgraded.vault });
    await waitFor(() => expect(result.current.buildings).toEqual(reloaded));
    expect(seen.map((r) => `${r.method} ${new URL(r.url).pathname}`)).toEqual([
      `GET /planets/${planetId}/buildings`,
      `POST /planets/${planetId}/buildings/metal_mine/upgrade`,
      `GET /planets/${planetId}/buildings`,
    ]);
  });

  it("shows the upgraded building while the list is read again", async () => {
    let resolveReload: (response: Response) => void = () => {};
    let reads = 0;
    const client = createApi(async (input: RequestInfo | URL, init?: RequestInit) => {
      const request = new Request(input, init);
      if (request.method === "GET") {
        reads += 1;
        if (reads === 1) {
          return Response.json(buildings);
        }
        return new Promise<Response>((resolve) => {
          resolveReload = resolve;
        });
      }
      return Response.json(upgraded);
    });
    const { result } = renderHook(() => useBuildings(planetId, client));
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.upgrade("metal_mine");
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.buildings[0]).toEqual(upgradedMetalMine);

    resolveReload(Response.json(reloaded));
    await waitFor(() => expect(result.current.buildings).toEqual(reloaded));
  });

  it("ignores an upgrade response that resolves after the planet changed", async () => {
    const otherPlanetId = "d1a9b7a0-6e1a-4c9e-9b8a-9a9e3d9a1a02";
    let resolveUpgrade: (response: Response) => void = () => {};
    const seen: Request[] = [];
    const client = createApi(async (input: RequestInfo | URL, init?: RequestInit) => {
      const request = new Request(input, init);
      seen.push(request);
      const path = new URL(request.url).pathname;
      if (request.method === "GET") {
        return Response.json(buildings);
      }
      if (path === `/planets/${planetId}/buildings/metal_mine/upgrade`) {
        return new Promise<Response>((resolve) => {
          resolveUpgrade = resolve;
        });
      }
      return new Response(null, { status: 404 });
    });

    const { result, rerender } = renderHook(({ id }) => useBuildings(id, client), {
      initialProps: { id: planetId },
    });
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome: unknown;
    const pending = result.current.upgrade("metal_mine").then((r) => (outcome = r));

    rerender({ id: otherPlanetId });
    await waitFor(() => expect(result.current.loading).toBe(false));
    const readsBefore = seen.filter((r) => r.method === "GET").length;

    resolveUpgrade(Response.json(upgraded));
    await act(async () => {
      await pending;
    });

    expect(outcome).toEqual({ status: 0 });
    expect(result.current.buildings).toEqual(buildings);
    expect(seen.filter((r) => r.method === "GET")).toHaveLength(readsBefore);
  });

  it("returns a 409 without changing the buildings or reading the list again", async () => {
    const seen: Request[] = [];
    const client = createApi(
      fakeFetch(
        {
          [`GET /planets/${planetId}/buildings`]: { status: 200, body: buildings },
          [`POST /planets/${planetId}/buildings/metal_mine/upgrade`]: {
            status: 409,
            body: { detail: "Not enough resources" },
          },
        },
        seen,
      ),
    );
    const { result } = renderHook(() => useBuildings(planetId, client));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome;
    await act(async () => {
      outcome = await result.current.upgrade("metal_mine");
    });

    expect(outcome).toEqual({ status: 409, detail: "Not enough resources" });
    expect(result.current.buildings).toEqual(buildings);
    expect(seen.filter((r) => r.method === "GET")).toHaveLength(1);
  });

  it("returns a 404 when the planet was not found", async () => {
    const client = createApi(
      fakeFetch({
        [`GET /planets/${planetId}/buildings`]: { status: 200, body: buildings },
        [`POST /planets/${planetId}/buildings/solar_plant/upgrade`]: {
          status: 404,
          body: { detail: "Not found" },
        },
      }),
    );
    const { result } = renderHook(() => useBuildings(planetId, client));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome;
    await act(async () => {
      outcome = await result.current.upgrade("solar_plant");
    });

    expect(outcome).toEqual({ status: 404, detail: "Not found" });
  });

  it("reloads the list on demand, for example when a countdown reaches 0", async () => {
    const seen: Request[] = [];
    const client = createApi(
      fakeFetch(
        {
          [`GET /planets/${planetId}/buildings`]: [
            { status: 200, body: buildings },
            { status: 200, body: reloaded },
          ],
        },
        seen,
      ),
    );
    const { result } = renderHook(() => useBuildings(planetId, client));
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.reload();
    });

    expect(result.current.buildings).toEqual(reloaded);
    expect(seen.filter((r) => r.method === "GET")).toHaveLength(2);
  });

  it("does nothing when reload is called without a planet", async () => {
    const client = createApi(fakeFetch({}));
    const { result } = renderHook(() => useBuildings(null, client));

    await act(async () => {
      await result.current.reload();
    });

    expect(result.current.buildings).toEqual([]);
  });
});
