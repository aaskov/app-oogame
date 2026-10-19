import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { createApi } from "@/lib/api";
import { useVault, type VaultResult } from "@/hooks/useVault";

afterEach(cleanup);

const planetId = "b2b7b8d0-6e1a-4c9e-9b8a-9a9e3d9a1a01";
const vault = {
  planet_id: planetId,
  metal: 500,
  crystal: 500,
  deuterium: 0,
  updated_at: "2026-10-19T00:00:00Z",
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

describe("useVault", () => {
  it("has no vault when planetId is null", async () => {
    const client = createApi(fakeFetch({}));
    const { result } = renderHook(() => useVault(null, client));

    expect(result.current.loading).toBe(false);
    expect(result.current.vault).toBeNull();
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
    expect(seen[0]?.url.endsWith(`/planets/${planetId}/vault`)).toBe(true);
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
    expect(result.current.error).toBe(404);
  });

  it("updates the vault with PATCH and stores the returned values", async () => {
    const seen: Request[] = [];
    const updated = { ...vault, metal: 1_500_000 };
    const client = createApi(
      fakeFetch(
        {
          [`GET /planets/${planetId}/vault`]: { status: 200, body: vault },
          [`PATCH /planets/${planetId}/vault`]: { status: 200, body: updated },
        },
        seen,
      ),
    );
    const { result } = renderHook(() => useVault(planetId, client));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome: VaultResult | undefined;
    await act(async () => {
      outcome = await result.current.update({ metal: 1_500_000 });
    });

    expect(outcome).toEqual({ ok: true });
    expect(result.current.vault).toEqual(updated);
    const patch = seen.find((r) => r.method === "PATCH");
    expect(await patch?.json()).toEqual({ metal: 1_500_000 });
  });

  it("reports a 422 from an update without changing the vault", async () => {
    const client = createApi(
      fakeFetch({
        [`GET /planets/${planetId}/vault`]: { status: 200, body: vault },
        [`PATCH /planets/${planetId}/vault`]: { status: 422 },
      }),
    );
    const { result } = renderHook(() => useVault(planetId, client));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome: VaultResult | undefined;
    await act(async () => {
      outcome = await result.current.update({ metal: -1 });
    });

    expect(outcome).toEqual({ ok: false, status: 422 });
    expect(result.current.vault).toEqual(vault);
  });
});
