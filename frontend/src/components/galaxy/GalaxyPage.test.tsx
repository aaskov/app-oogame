import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GalaxyPage } from "@/components/galaxy/GalaxyPage";
import { ada, fakeFetch, galaxySystem, homePlanet } from "@/components/galaxy/fakeFetch";
import { AuthContext } from "@/hooks/useAuth";
import { createApi } from "@/lib/api";

const { useParams, push } = vi.hoisted(() => ({
  useParams: vi.fn(() => ({ galaxy: "1", system: "23" })),
  push: vi.fn(),
}));
vi.mock("next/navigation", () => ({ useParams, useRouter: () => ({ push }) }));

afterEach(() => {
  cleanup();
  useParams.mockReturnValue({ galaxy: "1", system: "23" });
  push.mockClear();
});

function renderPage(routes: Parameters<typeof fakeFetch>[0]) {
  const client = createApi(fakeFetch(routes));
  render(
    <AuthContext.Provider
      value={{ user: ada, loading: false, login: vi.fn(), register: vi.fn(), logout: vi.fn() }}
    >
      <GalaxyPage client={client} />
    </AuthContext.Provider>,
  );
}

describe("GalaxyPage", () => {
  it("shows the 15 positions in order", async () => {
    renderPage({ "GET /galaxy/1/23": { status: 200, body: galaxySystem } });

    const items = await screen.findAllByRole("listitem");
    expect(items).toHaveLength(15);
    expect(items.map((item) => item.textContent)).toEqual(
      galaxySystem.positions.map((position) => {
        if (!position.planet) {
          return `[1:23:${position.position}]Free`;
        }
        const own = position.planet.username === ada.username ? " (your planet)" : "";
        return `[1:23:${position.position}]${position.planet.name} · ${position.planet.username}${own}`;
      }),
    );
  });

  it("shows the planet name and username at an occupied position", async () => {
    renderPage({ "GET /galaxy/1/23": { status: 200, body: galaxySystem } });

    const items = await screen.findAllByRole("listitem");
    const occupied = items.find((item) => item.textContent?.includes("Homeworld"));
    expect(occupied?.textContent).toContain("Homeworld · ada");
  });

  it("shows that a position is free", async () => {
    renderPage({ "GET /galaxy/1/23": { status: 200, body: galaxySystem } });

    const items = await screen.findAllByRole("listitem");
    expect(within(items[0]).getByText("Free")).toBeTruthy();
  });

  it("marks the logged-in player's own planet", async () => {
    renderPage({ "GET /galaxy/1/23": { status: 200, body: galaxySystem } });

    const items = await screen.findAllByRole("listitem");
    const own = items.find((item) => item.textContent?.includes("Homeworld"));
    const other = items.find((item) => item.textContent?.includes("Outpost"));
    expect(own?.textContent).toContain("your planet");
    expect(other?.textContent).not.toContain("your planet");
  });

  it("disables the previous button at system 1", async () => {
    useParams.mockReturnValue({ galaxy: "1", system: "1" });
    renderPage({ "GET /galaxy/1/1": { status: 200, body: { ...galaxySystem, system: 1 } } });

    expect(
      (await screen.findByRole("button", { name: "Previous system" })) as HTMLButtonElement,
    ).toHaveProperty("disabled", true);
    expect(screen.getByRole("button", { name: "Next system" })).toHaveProperty("disabled", false);
  });

  it("disables the next button at systems_per_galaxy", async () => {
    useParams.mockReturnValue({ galaxy: "1", system: "50" });
    renderPage({
      "GET /galaxy/1/50": { status: 200, body: { ...galaxySystem, system: 50, systems_per_galaxy: 50 } },
    });

    expect(
      (await screen.findByRole("button", { name: "Next system" })) as HTMLButtonElement,
    ).toHaveProperty("disabled", true);
    expect(screen.getByRole("button", { name: "Previous system" })).toHaveProperty("disabled", false);
  });

  it("goes to the next system on click", async () => {
    renderPage({ "GET /galaxy/1/23": { status: 200, body: galaxySystem } });
    await screen.findByRole("button", { name: "Next system" });

    fireEvent.click(screen.getByRole("button", { name: "Next system" }));

    expect(push).toHaveBeenCalledWith("/galaxy/1/24");
  });

  it("goes to the previous system on click", async () => {
    renderPage({ "GET /galaxy/1/23": { status: 200, body: galaxySystem } });
    await screen.findByRole("button", { name: "Previous system" });

    fireEvent.click(screen.getByRole("button", { name: "Previous system" }));

    expect(push).toHaveBeenCalledWith("/galaxy/1/22");
  });

  it("shows a message and a link to the home system on a 404", async () => {
    renderPage({
      "GET /galaxy/1/23": { status: 404, body: { detail: "Not found" } },
      "GET /planets": { status: 200, body: [homePlanet] },
    });

    expect((await screen.findByRole("alert")).textContent).toBe("This system was not found.");
    await waitFor(() =>
      expect(screen.getByRole("link", { name: "Go to the home system" }).getAttribute("href")).toBe(
        `/galaxy/${homePlanet.coordinates.galaxy}/${homePlanet.coordinates.system}`,
      ),
    );
  });

  it("gives each control a 44 px minimum tap target", async () => {
    renderPage({ "GET /galaxy/1/23": { status: 200, body: galaxySystem } });

    expect((await screen.findByRole("button", { name: "Next system" })).className).toContain("min-h-11");
  });
});
