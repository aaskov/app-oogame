import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TopBar } from "@/app/(game)/TopBar";
import { AuthProvider } from "@/components/auth/AuthProvider";
import { ada, fakeFetch as authFakeFetch } from "@/components/auth/fakeFetch";
import { colony, fakeFetch as planetsFakeFetch, homeworld } from "@/components/planets/fakeFetch";
import { createApi } from "@/lib/api";

const { useParams } = vi.hoisted(() => ({ useParams: vi.fn(() => ({})) }));
vi.mock("next/navigation", () => ({ useParams }));

afterEach(() => {
  cleanup();
  useParams.mockReturnValue({});
});

function renderTopBar(seen: Request[] = []) {
  const authApi = createApi(
    authFakeFetch({ "GET /auth/me": { status: 200, body: ada }, "POST /auth/logout": { status: 204 } }, seen),
  );
  const planetsApi = createApi(planetsFakeFetch({ "GET /planets": { status: 200, body: [homeworld, colony] } }));
  render(
    <AuthProvider api={authApi}>
      <TopBar client={planetsApi} />
    </AuthProvider>,
  );
}

describe("TopBar", () => {
  it("shows OOGame and a link to /homeworld when no planet is selected", async () => {
    renderTopBar();

    const link = await screen.findByRole("link", { name: "OOGame" });
    expect(link.getAttribute("href")).toBe("/homeworld");
  });

  it("shows the selected planet's name, still linking to /homeworld", async () => {
    useParams.mockReturnValue({ id: colony.id });
    renderTopBar();

    const link = await screen.findByRole("link", { name: "Colony" });
    expect(link.getAttribute("href")).toBe("/homeworld");
  });

  it("shows the selected planet's coordinates", async () => {
    useParams.mockReturnValue({ id: colony.id });
    renderTopBar();

    await screen.findByRole("link", { name: "Colony" });
    expect(screen.getByText("[1:23:9]")).toBeTruthy();
  });

  it("does not show coordinates when no planet is selected", async () => {
    renderTopBar();

    await screen.findByRole("link", { name: "OOGame" });
    expect(screen.queryByText("[1:23:7]")).toBeNull();
  });

  it("has a Galaxy link to the home planet's system", async () => {
    renderTopBar();

    const link = await screen.findByRole("link", { name: "Galaxy" });
    expect(link.getAttribute("href")).toBe("/galaxy/1/23");
  });

  it("logs out on click", async () => {
    const seen: Request[] = [];
    renderTopBar(seen);
    await screen.findByRole("link", { name: "OOGame" });

    fireEvent.click(screen.getByRole("button", { name: "Log out" }));

    await waitFor(() => expect(seen.some((r) => r.url.endsWith("/auth/logout"))).toBe(true));
  });
});
