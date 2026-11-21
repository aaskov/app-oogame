import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useResearch } from "@/hooks/useResearch";
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

const energyTechnology = {
  kind: "energy_technology",
  level: 0,
  cost: { metal: 0, crystal: 800, deuterium: 400 },
  available: true,
};
const plasmaTechnology = {
  kind: "plasma_technology",
  level: 0,
  cost: { metal: 2000, crystal: 4000, deuterium: 1000 },
  available: false,
};
const research = { technologies: [energyTechnology, plasmaTechnology] };

const started = {
  research: {
    technologies: [energyTechnology, plasmaTechnology],
    running: {
      kind: "energy_technology",
      planet_id: planetId,
      finishes_at: "2026-10-19T00:24:00Z",
    },
  },
  vault: {
    planet_id: planetId,
    metal: 500,
    crystal: 400,
    deuterium: 200,
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

describe("useResearch", () => {
  it("does not read the clock", async () => {
    const dateNow = vi.spyOn(Date, "now");
    const client = createApi(fakeFetch({ "GET /research": { status: 200, body: research } }));
    const { result } = renderHook(() => useResearch(client));
    expect(dateNow).not.toHaveBeenCalled();

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(dateNow).not.toHaveBeenCalled();
  });

  it("reads the research of the player", async () => {
    const seen: Request[] = [];
    const client = createApi(fakeFetch({ "GET /research": { status: 200, body: research } }, seen));
    const { result } = renderHook(() => useResearch(client));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.research).toEqual(research);
    expect(seen[0]?.url.endsWith("/research")).toBe(true);
  });

  it("sets the error status on a non-200", async () => {
    const client = createApi(
      fakeFetch({ "GET /research": { status: 401, body: { detail: "No valid session" } } }),
    );
    const { result } = renderHook(() => useResearch(client));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.research).toBeNull();
    expect(result.current.error).toBe(401);
  });

  it("starts a research and returns the research and the vault from the response", async () => {
    const seen: Request[] = [];
    const client = createApi(
      fakeFetch(
        {
          "GET /research": { status: 200, body: research },
          [`POST /planets/${planetId}/research/energy_technology/start`]: { status: 200, body: started },
        },
        seen,
      ),
    );
    const { result } = renderHook(() => useResearch(client));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome;
    await act(async () => {
      outcome = await result.current.start(planetId, "energy_technology");
    });

    expect(outcome).toEqual({ status: 200, research: started.research, vault: started.vault });
    expect(result.current.research).toEqual(started.research);
    expect(seen.map((r) => `${r.method} ${new URL(r.url).pathname}`)).toEqual([
      "GET /research",
      `POST /planets/${planetId}/research/energy_technology/start`,
    ]);
  });

  it("returns a 409 without changing the research", async () => {
    const client = createApi(
      fakeFetch({
        "GET /research": { status: 200, body: research },
        [`POST /planets/${planetId}/research/energy_technology/start`]: {
          status: 409,
          body: { detail: "The research lab of the planet has level 0" },
        },
      }),
    );
    const { result } = renderHook(() => useResearch(client));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome;
    await act(async () => {
      outcome = await result.current.start(planetId, "energy_technology");
    });

    expect(outcome).toEqual({ status: 409, detail: "The research lab of the planet has level 0" });
    expect(result.current.research).toEqual(research);
  });

  it("reloads the research on demand, for example when a countdown reaches 0", async () => {
    const reloaded = { technologies: [{ ...energyTechnology, level: 1 }, plasmaTechnology] };
    const seen: Request[] = [];
    const client = createApi(
      fakeFetch(
        {
          "GET /research": [
            { status: 200, body: research },
            { status: 200, body: reloaded },
          ],
        },
        seen,
      ),
    );
    const { result } = renderHook(() => useResearch(client));
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.reload();
    });

    expect(result.current.research).toEqual(reloaded);
    expect(seen.filter((r) => r.method === "GET")).toHaveLength(2);
  });
});
