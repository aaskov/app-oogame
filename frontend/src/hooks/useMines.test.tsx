import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { createApi } from "@/lib/api";
import { useMines } from "@/hooks/useMines";

afterEach(cleanup);

const planetId = "b2b7b8d0-6e1a-4c9e-9b8a-9a9e3d9a1a01";

const mines = [
  { kind: "metal_mine", level: 0, production_per_hour: 0, upgrade_cost: { metal: 60, crystal: 15, deuterium: 0 } },
  { kind: "crystal_mine", level: 0, production_per_hour: 0, upgrade_cost: { metal: 48, crystal: 24, deuterium: 0 } },
];

const upgraded = {
  mine: { kind: "metal_mine", level: 1, production_per_hour: 33, upgrade_cost: { metal: 90, crystal: 22, deuterium: 0 } },
  vault: {
    planet_id: planetId,
    metal: 940,
    crystal: 985,
    deuterium: 0,
    production_per_hour: { metal: 63, crystal: 15, deuterium: 0 },
    calculated_at: "2026-10-19T00:05:00Z",
  },
};

type Route = { status: number; body?: unknown };

function fakeFetch(routes: Record<string, Route>, seen: Request[] = []) {
  return async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = new Request(input, init);
    seen.push(request);
    const route = routes[`${request.method} ${new URL(request.url).pathname}`];
    if (!route) {
      return new Response(null, { status: 404 });
    }
    return new Response(route.body === undefined ? null : JSON.stringify(route.body), {
      status: route.status,
      headers: { "Content-Type": "application/json" },
    });
  };
}

describe("useMines", () => {
  it("has no mines when planetId is null", async () => {
    const client = createApi(fakeFetch({}));
    const { result } = renderHook(() => useMines(null, client));

    expect(result.current.loading).toBe(false);
    expect(result.current.mines).toEqual([]);
  });

  it("lists the mines of the given planet", async () => {
    const seen: Request[] = [];
    const client = createApi(
      fakeFetch({ [`GET /planets/${planetId}/mines`]: { status: 200, body: mines } }, seen),
    );
    const { result } = renderHook(() => useMines(planetId, client));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.mines).toEqual(mines);
    expect(seen[0]?.url.endsWith(`/planets/${planetId}/mines`)).toBe(true);
  });

  it("sets the error status on a 404", async () => {
    const client = createApi(
      fakeFetch({
        [`GET /planets/${planetId}/mines`]: { status: 404, body: { detail: "Not found" } },
      }),
    );
    const { result } = renderHook(() => useMines(planetId, client));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.mines).toEqual([]);
    expect(result.current.error).toBe(404);
  });

  it("upgrades a mine and returns the new mine and vault", async () => {
    const seen: Request[] = [];
    const client = createApi(
      fakeFetch(
        {
          [`GET /planets/${planetId}/mines`]: { status: 200, body: mines },
          [`POST /planets/${planetId}/mines/metal_mine/upgrade`]: { status: 200, body: upgraded },
        },
        seen,
      ),
    );
    const { result } = renderHook(() => useMines(planetId, client));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome;
    await act(async () => {
      outcome = await result.current.upgrade("metal_mine");
    });

    expect(outcome).toEqual({ status: 200, mine: upgraded.mine, vault: upgraded.vault });
    expect(result.current.mines.find((m) => m.kind === "metal_mine")).toEqual(upgraded.mine);
    expect(seen.some((r) => r.method === "POST")).toBe(true);
  });

  it("ignores an upgrade response that resolves after the planet changed", async () => {
    const otherPlanetId = "d1a9b7a0-6e1a-4c9e-9b8a-9a9e3d9a1a02";
    let resolveUpgrade: (response: Response) => void = () => {};
    const client = createApi(async (input: RequestInfo | URL, init?: RequestInit) => {
      const request = new Request(input, init);
      const path = new URL(request.url).pathname;
      if (request.method === "GET") {
        return new Response(JSON.stringify(mines), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (path === `/planets/${planetId}/mines/metal_mine/upgrade`) {
        return new Promise<Response>((resolve) => {
          resolveUpgrade = resolve;
        });
      }
      return new Response(null, { status: 404 });
    });

    const { result, rerender } = renderHook(({ id }) => useMines(id, client), {
      initialProps: { id: planetId },
    });
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome: unknown;
    const pending = result.current.upgrade("metal_mine").then((r) => (outcome = r));

    rerender({ id: otherPlanetId });
    await waitFor(() => expect(result.current.loading).toBe(false));

    resolveUpgrade(
      new Response(JSON.stringify(upgraded), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    await act(async () => {
      await pending;
    });

    expect(outcome).toEqual({ status: 0 });
    expect(result.current.mines.find((m) => m.kind === "metal_mine")).toEqual(mines[0]);
  });

  it("returns a 409 without changing the mines when resources are too low", async () => {
    const client = createApi(
      fakeFetch({
        [`GET /planets/${planetId}/mines`]: { status: 200, body: mines },
        [`POST /planets/${planetId}/mines/metal_mine/upgrade`]: {
          status: 409,
          body: { detail: "Not enough resources" },
        },
      }),
    );
    const { result } = renderHook(() => useMines(planetId, client));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome;
    await act(async () => {
      outcome = await result.current.upgrade("metal_mine");
    });

    expect(outcome).toEqual({ status: 409 });
    expect(result.current.mines).toEqual(mines);
  });

  it("returns a 404 when the planet was not found", async () => {
    const client = createApi(
      fakeFetch({
        [`GET /planets/${planetId}/mines`]: { status: 200, body: mines },
        [`POST /planets/${planetId}/mines/metal_mine/upgrade`]: {
          status: 404,
          body: { detail: "Not found" },
        },
      }),
    );
    const { result } = renderHook(() => useMines(planetId, client));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome;
    await act(async () => {
      outcome = await result.current.upgrade("metal_mine");
    });

    expect(outcome).toEqual({ status: 404 });
  });
});
