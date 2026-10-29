import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useShipyard } from "@/hooks/useShipyard";
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

const smallCargo = {
  kind: "small_cargo",
  count: 0,
  cost: { metal: 2000, crystal: 2000, deuterium: 0 },
  build_seconds: 2880,
};
const lightFighter = {
  kind: "light_fighter",
  count: 0,
  cost: { metal: 3000, crystal: 1000, deuterium: 0 },
  build_seconds: 3600,
};
const shipyard = { ships: [smallCargo, lightFighter] };

const ordered = {
  shipyard: {
    ships: [
      { ...smallCargo, count: 0 },
      lightFighter,
    ],
    order: {
      kind: "small_cargo",
      remaining: 3,
      next_finishes_at: "2026-10-19T00:48:00Z",
      finishes_at: "2026-10-19T02:24:00Z",
    },
  },
  vault: {
    planet_id: planetId,
    metal: 4000,
    crystal: 4000,
    deuterium: 0,
    production_per_hour: { metal: 30, crystal: 15, deuterium: 0 },
    energy: { produced: 22, used: 22 },
    capacity: { metal: 10000, crystal: 10000, deuterium: 10000 },
    calculated_at: "2026-10-19T00:00:00Z",
  },
};

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

describe("useShipyard", () => {
  it("has no shipyard when planetId is null", () => {
    const client = createApi(fakeFetch({}));
    const { result } = renderHook(() => useShipyard(null, client));

    expect(result.current.loading).toBe(false);
    expect(result.current.shipyard).toBeNull();
  });

  it("does not read the clock", async () => {
    const dateNow = vi.spyOn(Date, "now");
    const client = createApi(fakeFetch({ [`GET /planets/${planetId}/ships`]: { status: 200, body: shipyard } }));
    const { result } = renderHook(() => useShipyard(planetId, client));
    expect(dateNow).not.toHaveBeenCalled();

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(dateNow).not.toHaveBeenCalled();
  });

  it("reads the shipyard of the given planet", async () => {
    const seen: Request[] = [];
    const client = createApi(
      fakeFetch({ [`GET /planets/${planetId}/ships`]: { status: 200, body: shipyard } }, seen),
    );
    const { result } = renderHook(() => useShipyard(planetId, client));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.shipyard).toEqual(shipyard);
    expect(seen[0]?.url.endsWith(`/planets/${planetId}/ships`)).toBe(true);
  });

  it("sets the error status on a 404", async () => {
    const client = createApi(
      fakeFetch({ [`GET /planets/${planetId}/ships`]: { status: 404, body: { detail: "Not found" } } }),
    );
    const { result } = renderHook(() => useShipyard(planetId, client));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.shipyard).toBeNull();
    expect(result.current.error).toBe(404);
  });

  it("orders ships and returns the vault and the shipyard from the response", async () => {
    const seen: Request[] = [];
    const client = createApi(
      fakeFetch(
        {
          [`GET /planets/${planetId}/ships`]: { status: 200, body: shipyard },
          [`POST /planets/${planetId}/ships/small_cargo/order`]: { status: 200, body: ordered },
        },
        seen,
      ),
    );
    const { result } = renderHook(() => useShipyard(planetId, client));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome;
    await act(async () => {
      outcome = await result.current.order("small_cargo", 3);
    });

    expect(outcome).toEqual({ status: 200, shipyard: ordered.shipyard, vault: ordered.vault });
    expect(result.current.shipyard).toEqual(ordered.shipyard);
    expect(seen.map((r) => `${r.method} ${new URL(r.url).pathname}`)).toEqual([
      `GET /planets/${planetId}/ships`,
      `POST /planets/${planetId}/ships/small_cargo/order`,
    ]);
    const body = await seen[1]!.json();
    expect(body).toEqual({ count: 3 });
  });

  it("returns a 409 without changing the shipyard", async () => {
    const client = createApi(
      fakeFetch({
        [`GET /planets/${planetId}/ships`]: { status: 200, body: shipyard },
        [`POST /planets/${planetId}/ships/small_cargo/order`]: {
          status: 409,
          body: { detail: "The shipyard has level 0" },
        },
      }),
    );
    const { result } = renderHook(() => useShipyard(planetId, client));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome;
    await act(async () => {
      outcome = await result.current.order("small_cargo", 1);
    });

    expect(outcome).toEqual({ status: 409, detail: "The shipyard has level 0" });
    expect(result.current.shipyard).toEqual(shipyard);
  });

  it("returns a 404 when the planet was not found", async () => {
    const client = createApi(
      fakeFetch({
        [`GET /planets/${planetId}/ships`]: { status: 200, body: shipyard },
        [`POST /planets/${planetId}/ships/small_cargo/order`]: { status: 404, body: { detail: "Not found" } },
      }),
    );
    const { result } = renderHook(() => useShipyard(planetId, client));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome;
    await act(async () => {
      outcome = await result.current.order("small_cargo", 1);
    });

    expect(outcome).toEqual({ status: 404, detail: "Not found" });
  });

  it("ignores an order response that resolves after the planet changed", async () => {
    const otherPlanetId = "d1a9b7a0-6e1a-4c9e-9b8a-9a9e3d9a1a02";
    let resolveOrder: (response: Response) => void = () => {};
    const seen: Request[] = [];
    const client = createApi(async (input: RequestInfo | URL, init?: RequestInit) => {
      const request = new Request(input, init);
      seen.push(request);
      const path = new URL(request.url).pathname;
      if (request.method === "GET") {
        return Response.json(shipyard);
      }
      if (path === `/planets/${planetId}/ships/small_cargo/order`) {
        return new Promise<Response>((resolve) => {
          resolveOrder = resolve;
        });
      }
      return new Response(null, { status: 404 });
    });

    const { result, rerender } = renderHook(({ id }) => useShipyard(id, client), {
      initialProps: { id: planetId },
    });
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome: unknown;
    const pending = result.current.order("small_cargo", 1).then((r) => (outcome = r));

    rerender({ id: otherPlanetId });
    await waitFor(() => expect(result.current.loading).toBe(false));

    resolveOrder(Response.json(ordered));
    await act(async () => {
      await pending;
    });

    expect(outcome).toEqual({ status: 0 });
    expect(result.current.shipyard).toEqual(shipyard);
  });

  it("reloads the shipyard on demand, for example when a countdown reaches 0", async () => {
    const reloaded = { ships: [{ ...smallCargo, count: 1 }, lightFighter] };
    const seen: Request[] = [];
    const client = createApi(
      fakeFetch(
        {
          [`GET /planets/${planetId}/ships`]: [
            { status: 200, body: shipyard },
            { status: 200, body: reloaded },
          ],
        },
        seen,
      ),
    );
    const { result } = renderHook(() => useShipyard(planetId, client));
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.reload();
    });

    expect(result.current.shipyard).toEqual(reloaded);
    expect(seen.filter((r) => r.method === "GET")).toHaveLength(2);
  });

  it("does nothing when reload is called without a planet", async () => {
    const client = createApi(fakeFetch({}));
    const { result } = renderHook(() => useShipyard(null, client));

    await act(async () => {
      await result.current.reload();
    });

    expect(result.current.shipyard).toBeNull();
  });
});
