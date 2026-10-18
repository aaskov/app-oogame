import { describe, expect, it } from "vitest";

import { createApi, getHealth } from "@/lib/api";

function fakeFetch(status: number, body: unknown, seen: Request[] = []) {
  return async (input: RequestInfo | URL, init?: RequestInit) => {
    seen.push(new Request(input, init));
    return new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  };
}

describe("getHealth", () => {
  it("returns the health from the backend", async () => {
    await expect(getHealth(createApi(fakeFetch(200, { status: "ok" })))).resolves.toEqual({
      status: "ok",
    });
  });

  it("fails on an error status", async () => {
    await expect(getHealth(createApi(fakeFetch(503, { detail: "down" })))).rejects.toThrow("503");
  });
});

describe("api", () => {
  it("sends the session cookie with each request", async () => {
    const seen: Request[] = [];
    await createApi(fakeFetch(200, { status: "ok" }, seen)).GET("/health");

    expect(seen[0]?.credentials).toBe("include");
  });
});
