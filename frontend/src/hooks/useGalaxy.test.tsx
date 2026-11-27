import { cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { useGalaxy } from "@/hooks/useGalaxy";
import { createApi } from "@/lib/api";

afterEach(cleanup);

type Reply = { status: number; body?: unknown };

function fakeFetch(routes: Record<string, Reply>, seen: Request[] = []) {
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

const system = {
  galaxy: 1,
  system: 23,
  galaxies: 1,
  systems_per_galaxy: 50,
  positions: [
    { position: 1 },
    { position: 2, planet: { name: "Homeworld", username: "ada" } },
  ],
};

describe("useGalaxy", () => {
  it("reads the system of the given galaxy and system", async () => {
    const seen: Request[] = [];
    const client = createApi(fakeFetch({ "GET /galaxy/1/23": { status: 200, body: system } }, seen));
    const { result } = renderHook(() => useGalaxy(1, 23, client));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.system).toEqual(system);
    expect(seen[0]?.url.endsWith("/galaxy/1/23")).toBe(true);
  });

  it("sets the error status on a 404", async () => {
    const client = createApi(
      fakeFetch({ "GET /galaxy/1/99": { status: 404, body: { detail: "Not found" } } }),
    );
    const { result } = renderHook(() => useGalaxy(1, 99, client));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.system).toBeNull();
    expect(result.current.error).toBe(404);
  });

  it("reads again when the galaxy or system changes", async () => {
    const otherSystem = { ...system, system: 24 };
    const seen: Request[] = [];
    const client = createApi(
      fakeFetch(
        {
          "GET /galaxy/1/23": { status: 200, body: system },
          "GET /galaxy/1/24": { status: 200, body: otherSystem },
        },
        seen,
      ),
    );
    const { result, rerender } = renderHook(({ s }) => useGalaxy(1, s, client), {
      initialProps: { s: 23 },
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.system).toEqual(system);

    rerender({ s: 24 });

    await waitFor(() => expect(result.current.system).toEqual(otherSystem));
    expect(seen.map((r) => new URL(r.url).pathname)).toEqual(["/galaxy/1/23", "/galaxy/1/24"]);
  });
});
