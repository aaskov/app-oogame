import { describe, expect, it } from "vitest";

import { getHealth } from "@/lib/api";

describe("getHealth", () => {
  it("returns the health from the backend", async () => {
    const fetcher = async () => new Response(JSON.stringify({ status: "ok" }), { status: 200 });

    await expect(getHealth(fetcher)).resolves.toEqual({ status: "ok" });
  });

  it("fails on an error status", async () => {
    const fetcher = async () => new Response("", { status: 503 });

    await expect(getHealth(fetcher)).rejects.toThrow("503");
  });
});
