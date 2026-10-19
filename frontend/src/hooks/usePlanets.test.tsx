import { cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { createApi } from "@/lib/api";
import { usePlanets } from "@/hooks/usePlanets";

afterEach(cleanup);

const homeworld = { id: "b2b7b8d0-6e1a-4c9e-9b8a-9a9e3d9a1a01", name: "Homeworld" };
const colony = { id: "d1a9b7a0-6e1a-4c9e-9b8a-9a9e3d9a1a02", name: "Colony" };

function fakeFetch(status: number, body: unknown, seen: Request[] = []) {
  return async (input: RequestInfo | URL, init?: RequestInit) => {
    seen.push(new Request(input, init));
    return new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  };
}

describe("usePlanets", () => {
  it("lists the planets of the user", async () => {
    const seen: Request[] = [];
    const client = createApi(fakeFetch(200, [homeworld, colony], seen));
    const { result } = renderHook(() => usePlanets(client));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.planets).toEqual([homeworld, colony]);
    expect(seen[0]?.method).toBe("GET");
    expect(seen[0]?.url.endsWith("/planets")).toBe(true);
  });

  it("has an error status on a failure response", async () => {
    const client = createApi(fakeFetch(401, { detail: "No session" }));
    const { result } = renderHook(() => usePlanets(client));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.planets).toEqual([]);
    expect(result.current.error).toBe(401);
  });

  it("has no planets when the request fails outright", async () => {
    const client = createApi(async () => {
      throw new TypeError("network down");
    });
    const { result } = renderHook(() => usePlanets(client));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.planets).toEqual([]);
    expect(result.current.error).toBe(0);
  });
});
