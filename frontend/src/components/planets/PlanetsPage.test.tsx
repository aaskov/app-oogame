import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PlanetsPage } from "@/components/planets/PlanetsPage";
import {
  buildingUpgrade,
  buildings,
  buildingsAfterUpgrade,
  buildingsUpgrading,
  colony,
  fakeFetch,
  homeworld,
  vault,
} from "@/components/planets/fakeFetch";
import { AuthContext, useAuthState } from "@/hooks/useAuth";
import { createApi } from "@/lib/api";

const { replace } = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));

const ada = { id: "6f1c2b9e-0d5a-4c57-9d57-3a1f6f0b8a11", email: "ada@example.com" };

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(new Date(vault.calculated_at));
});

afterEach(() => {
  cleanup();
  replace.mockClear();
  vi.useRealTimers();
});

function renderPage(routes: Parameters<typeof fakeFetch>[0], seen: Request[] = []) {
  const client = createApi(fakeFetch(routes, seen));
  function Wrapper({ children }: { children: ReactNode }) {
    return <AuthContext.Provider value={useAuthState(client)}>{children}</AuthContext.Provider>;
  }
  render(
    <Wrapper>
      <PlanetsPage client={client} />
    </Wrapper>,
  );
}

describe("PlanetsPage", () => {
  it("sends a user who is not logged in to /login", async () => {
    renderPage({ "GET /auth/me": { status: 401 } });

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });

  it("lists the planets and selects the first one", async () => {
    renderPage({
      "GET /auth/me": { status: 200, body: ada },
      "GET /planets": { status: 200, body: [homeworld, colony] },
      [`GET /planets/${homeworld.id}/vault`]: { status: 200, body: vault },
      [`GET /planets/${homeworld.id}/buildings`]: { status: 200, body: buildings },
    });

    expect(await screen.findByRole("button", { name: "Homeworld" })).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Homeworld" }).getAttribute("aria-pressed"),
    ).toBe("true");
    expect((await screen.findByText("Metal")).nextElementSibling?.textContent).toBe("500 / 10,000");
    expect(replace).not.toHaveBeenCalled();
  });

  it("shows the vault of the planet the user selects", async () => {
    renderPage({
      "GET /auth/me": { status: 200, body: ada },
      "GET /planets": { status: 200, body: [homeworld, colony] },
      [`GET /planets/${homeworld.id}/vault`]: { status: 200, body: vault },
      [`GET /planets/${homeworld.id}/buildings`]: { status: 200, body: buildings },
      [`GET /planets/${colony.id}/vault`]: {
        status: 200,
        body: { ...vault, planet_id: colony.id, metal: 42 },
      },
      [`GET /planets/${colony.id}/buildings`]: { status: 200, body: buildings },
    });

    await screen.findByText("Metal");
    fireEvent.click(screen.getByRole("button", { name: "Colony" }));

    await waitFor(() =>
      expect(screen.getByText("Metal").nextElementSibling?.textContent).toBe("42 / 10,000"),
    );
  });

  it("shows the four buildings and the energy line", async () => {
    renderPage({
      "GET /auth/me": { status: 200, body: ada },
      "GET /planets": { status: 200, body: [homeworld] },
      [`GET /planets/${homeworld.id}/vault`]: { status: 200, body: vault },
      [`GET /planets/${homeworld.id}/buildings`]: { status: 200, body: buildings },
    });

    expect(await screen.findByText("Solar plant")).toBeTruthy();
    expect(screen.getByText("Metal mine")).toBeTruthy();
    expect(screen.getByText("Energy: 22 / 22")).toBeTruthy();
    expect(screen.queryByText(/Energy is too low/)).toBeNull();
  });

  it("updates the vault, the energy warning, and the other mines after a 200 upgrade", async () => {
    const seen: Request[] = [];
    renderPage(
      {
        "GET /auth/me": { status: 200, body: ada },
        "GET /planets": { status: 200, body: [homeworld, colony] },
        [`GET /planets/${homeworld.id}/vault`]: {
          status: 200,
          body: { ...vault, metal: 1000, crystal: 1000 },
        },
        [`GET /planets/${homeworld.id}/buildings`]: [
          { status: 200, body: buildings },
          { status: 200, body: buildingsAfterUpgrade },
        ],
        [`POST /planets/${homeworld.id}/buildings/metal_mine/upgrade`]: {
          status: 200,
          body: buildingUpgrade,
        },
      },
      seen,
    );

    expect(await screen.findByText("Metal mine")).toBeTruthy();

    fireEvent.click(await screen.findByRole("button", { name: "Upgrade Metal mine" }));

    await waitFor(() => expect(screen.getByText("Metal").nextElementSibling?.textContent).toBe("410 / 10,000"));
    expect(screen.getByText("Energy: 22 / 35")).toBeTruthy();
    expect(screen.getByText("Energy is too low. Mines produce 62 %.")).toBeTruthy();
    await waitFor(() => expect(screen.getByText("Level 1 · +13/h")).toBeTruthy());
    expect(screen.getByText("Level 2 · +45/h")).toBeTruthy();
    expect(seen.some((r) => new URL(r.url).pathname.endsWith("/mines"))).toBe(false);
  });

  it("reads the buildings and the vault again when a running upgrade finishes", async () => {
    const seen: Request[] = [];
    renderPage(
      {
        "GET /auth/me": { status: 200, body: ada },
        "GET /planets": { status: 200, body: [homeworld] },
        [`GET /planets/${homeworld.id}/vault`]: [
          { status: 200, body: vault },
          { status: 200, body: { ...vault, metal: 999 } },
        ],
        [`GET /planets/${homeworld.id}/buildings`]: [
          { status: 200, body: buildingsUpgrading },
          { status: 200, body: buildingsAfterUpgrade },
        ],
      },
      seen,
    );

    expect(await screen.findByText("Upgrading to level 2 · 1:48")).toBeTruthy();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(108_000);
    });

    await waitFor(() => expect(screen.getByText("Level 2 · +45/h")).toBeTruthy());
    await waitFor(() => expect(screen.getByText("Metal").nextElementSibling?.textContent).toBe("999 / 10,000"));
    expect(seen.filter((r) => r.method === "GET" && new URL(r.url).pathname.endsWith("/buildings"))).toHaveLength(2);
    expect(seen.filter((r) => r.method === "GET" && new URL(r.url).pathname.endsWith("/vault"))).toHaveLength(2);
  });
});
