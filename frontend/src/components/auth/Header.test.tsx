import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { AuthProvider } from "@/components/auth/AuthProvider";
import { Header } from "@/components/auth/Header";
import { ada, fakeFetch } from "@/components/auth/fakeFetch";
import { createApi } from "@/lib/api";

afterEach(cleanup);

function renderHeader(routes: Parameters<typeof fakeFetch>[0], seen: Request[] = []) {
  render(
    <AuthProvider api={createApi(fakeFetch(routes, seen))}>
      <Header />
    </AuthProvider>,
  );
}

describe("Header", () => {
  it("shows links to /login and /register without a user", async () => {
    renderHeader({ "GET /auth/me": { status: 401 } });

    const login = await screen.findByRole("link", { name: "Log in" });
    expect(login.getAttribute("href")).toBe("/login");
    expect(screen.getByRole("link", { name: "Register" }).getAttribute("href")).toBe("/register");
    expect(screen.queryByRole("button", { name: "Log out" })).toBeNull();
  });

  it("shows the email and a logout button for a logged-in user", async () => {
    renderHeader({ "GET /auth/me": { status: 200, body: ada } });

    expect(await screen.findByText("ada@example.com")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Log out" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Log in" })).toBeNull();
  });

  it("shows neither while the user loads", () => {
    renderHeader({ "GET /auth/me": { status: 200, body: ada } });

    expect(screen.queryByRole("link", { name: "Log in" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Log out" })).toBeNull();
  });

  it("logs out on click and shows the links again", async () => {
    const seen: Request[] = [];
    renderHeader(
      { "GET /auth/me": { status: 200, body: ada }, "POST /auth/logout": { status: 204 } },
      seen,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Log out" }));

    await waitFor(() => expect(screen.getByRole("link", { name: "Log in" })).toBeTruthy());
    expect(seen.some((r) => r.method === "POST" && r.url.endsWith("/auth/logout"))).toBe(true);
  });
});
