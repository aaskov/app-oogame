import { cleanup, renderHook, waitFor, act } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { ada, fakeFetch } from "@/components/auth/fakeFetch";
import { createApi } from "@/lib/api";
import { AuthContext, useAuth, useAuthState, type AuthResult } from "@/hooks/useAuth";

afterEach(cleanup);

const credentials = { email: "ada@example.com", password: "correct horse" };

function setup(routes: Parameters<typeof fakeFetch>[0]) {
  const seen: Request[] = [];
  const client = createApi(fakeFetch(routes, seen));
  function Wrapper({ children }: { children: ReactNode }) {
    return <AuthContext.Provider value={useAuthState(client)}>{children}</AuthContext.Provider>;
  }
  return { seen, ...renderHook(() => useAuth(), { wrapper: Wrapper }) };
}

describe("useAuth", () => {
  it("reads the current user from GET /auth/me", async () => {
    const { result, seen } = setup({ "GET /auth/me": { status: 200, body: ada } });

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.user).toEqual(ada);
    expect(seen[0]?.method).toBe("GET");
  });

  it("has no user on a 401 from /auth/me", async () => {
    const { result } = setup({ "GET /auth/me": { status: 401, body: { detail: "No session" } } });

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.user).toBeNull();
  });

  it("has no user when the request fails", async () => {
    const client = createApi(async () => {
      throw new TypeError("network down");
    });
    const { result } = renderHook(() => useAuthState(client));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.user).toBeNull();
  });

  it("logs in and sets the user", async () => {
    const { result, seen } = setup({
      "GET /auth/me": { status: 401 },
      "POST /auth/login": { status: 200, body: ada },
    });
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome: AuthResult | undefined;
    await act(async () => {
      outcome = await result.current.login(credentials);
    });

    expect(outcome).toEqual({ ok: true });
    expect(result.current.user).toEqual(ada);
    const request = seen.find((r) => r.url.endsWith("/auth/login"));
    expect(await request?.json()).toEqual(credentials);
  });

  it("reports a failed login and keeps the user empty", async () => {
    const { result } = setup({
      "GET /auth/me": { status: 401 },
      "POST /auth/login": { status: 401, body: { detail: "Wrong email or password" } },
    });
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome: AuthResult | undefined;
    await act(async () => {
      outcome = await result.current.login(credentials);
    });

    expect(outcome).toEqual({ ok: false, status: 401 });
    expect(result.current.user).toBeNull();
  });

  it("reports status 0 when the login request fails", async () => {
    const client = createApi(async (input, init) => {
      if (new Request(input, init).method === "GET") {
        return new Response(null, { status: 401 });
      }
      throw new TypeError("network down");
    });
    const { result } = renderHook(() => useAuthState(client));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome: AuthResult | undefined;
    await act(async () => {
      outcome = await result.current.login(credentials);
    });

    expect(outcome).toEqual({ ok: false, status: 0 });
  });

  it("registers and then logs the user in", async () => {
    const { result, seen } = setup({
      "GET /auth/me": { status: 401 },
      "POST /auth/register": { status: 201, body: ada },
      "POST /auth/login": { status: 200, body: ada },
    });
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome: AuthResult | undefined;
    await act(async () => {
      outcome = await result.current.register(credentials);
    });

    expect(outcome).toEqual({ ok: true });
    expect(result.current.user).toEqual(ada);
    expect(seen.map((r) => `${r.method} ${new URL(r.url).pathname}`)).toEqual([
      "GET /auth/me",
      "POST /auth/register",
      "POST /auth/login",
    ]);
  });

  it("does not log in when register fails", async () => {
    const { result, seen } = setup({
      "GET /auth/me": { status: 401 },
      "POST /auth/register": { status: 409, body: { detail: "Email exists" } },
    });
    await waitFor(() => expect(result.current.loading).toBe(false));

    let outcome: AuthResult | undefined;
    await act(async () => {
      outcome = await result.current.register(credentials);
    });

    expect(outcome).toEqual({ ok: false, status: 409 });
    expect(result.current.user).toBeNull();
    expect(seen.some((r) => r.url.endsWith("/auth/login"))).toBe(false);
  });

  it("logs out and clears the user", async () => {
    const { result, seen } = setup({
      "GET /auth/me": { status: 200, body: ada },
      "POST /auth/logout": { status: 204 },
    });
    await waitFor(() => expect(result.current.user).toEqual(ada));

    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.user).toBeNull();
    expect(seen.some((r) => r.method === "POST" && r.url.endsWith("/auth/logout"))).toBe(true);
  });

  it("never reads or stores a token", async () => {
    const { result, seen } = setup({
      "GET /auth/me": { status: 401 },
      "POST /auth/login": { status: 200, body: { ...ada, token: "secret" } },
    });
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.login(credentials);
    });

    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    expect(document.cookie).toBe("");
    expect(seen.every((r) => !r.headers.has("Authorization"))).toBe(true);
    expect(seen.every((r) => r.credentials === "include")).toBe(true);
  });

  it("throws outside a provider", () => {
    expect(() => renderHook(() => useAuth())).toThrow("AuthProvider");
  });
});
