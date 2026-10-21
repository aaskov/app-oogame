import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createApi } from "@/lib/api";
import { useVault } from "@/hooks/useVault";

afterEach(cleanup);

const planetId = "b2b7b8d0-6e1a-4c9e-9b8a-9a9e3d9a1a01";
const vault = {
  planet_id: planetId,
  metal: 500,
  crystal: 500,
  deuterium: 0,
  production_per_hour: { metal: 3600, crystal: 1800, deuterium: 0 },
  calculated_at: "2026-10-19T00:00:00.000Z",
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

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(new Date(vault.calculated_at));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useVault", () => {
  it("has no vault when planetId is null", async () => {
    const client = createApi(fakeFetch({}));
    const { result } = renderHook(() => useVault(null, client));

    expect(result.current.loading).toBe(false);
    expect(result.current.vault).toBeNull();
    expect(result.current.amounts).toBeNull();
  });

  it("does not read the clock while rendering, only from an effect", () => {
    const now = vi.spyOn(Date, "now");
    const client = createApi(fakeFetch({}));

    renderHook(() => useVault(null, client));

    // With no planetId, no effect runs (there is nothing to fetch and no vault
    // to tick), so a clock read here could only have come from the render
    // itself. Next.js treats that as an unstable value during prerendering
    // (https://nextjs.org/docs/messages/blocking-prerender-current-time-client).
    expect(now).not.toHaveBeenCalled();
  });

  it("reads the vault of the given planet", async () => {
    const seen: Request[] = [];
    const client = createApi(
      fakeFetch({ [`GET /planets/${planetId}/vault`]: { status: 200, body: vault } }, seen),
    );
    const { result } = renderHook(() => useVault(planetId, client));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.vault).toEqual(vault);
    expect(result.current.amounts).toEqual({ metal: 500, crystal: 500, deuterium: 0 });
    expect(seen[0]?.url.endsWith(`/planets/${planetId}/vault`)).toBe(true);
  });

  it("counts the amounts up each second from production_per_hour", async () => {
    const client = createApi(
      fakeFetch({ [`GET /planets/${planetId}/vault`]: { status: 200, body: vault } }),
    );
    const { result } = renderHook(() => useVault(planetId, client));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.amounts).toEqual({ metal: 500, crystal: 500, deuterium: 0 });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(result.current.amounts).toEqual({ metal: 501, crystal: 500, deuterium: 0 });
  });

  it("sets the error status on a 404", async () => {
    const client = createApi(
      fakeFetch({
        [`GET /planets/${planetId}/vault`]: { status: 404, body: { detail: "Not found" } },
      }),
    );
    const { result } = renderHook(() => useVault(planetId, client));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.vault).toBeNull();
    expect(result.current.amounts).toBeNull();
    expect(result.current.error).toBe(404);
  });

  it("lets a caller replace the vault, for example after an upgrade", async () => {
    const client = createApi(
      fakeFetch({ [`GET /planets/${planetId}/vault`]: { status: 200, body: vault } }),
    );
    const { result } = renderHook(() => useVault(planetId, client));

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.setVault({
        ...vault,
        metal: 10,
        calculated_at: new Date().toISOString(),
      });
    });

    expect(result.current.amounts).toEqual({ metal: 10, crystal: 500, deuterium: 0 });
  });
});
