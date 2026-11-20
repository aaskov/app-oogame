import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { BuildingsPage } from "@/components/planets/BuildingsPage";
import { buildingUpgrade, buildings, fakeFetch, homeworld } from "@/components/planets/fakeFetch";
import { VaultContext } from "@/hooks/useVault";
import { createApi } from "@/lib/api";

const { useParams } = vi.hoisted(() => ({ useParams: vi.fn(() => ({ id: homeworld.id })) }));
vi.mock("next/navigation", () => ({ useParams }));

afterEach(cleanup);

function renderPage(
  routes: Parameters<typeof fakeFetch>[0],
  amounts: { metal: number; crystal: number; deuterium: number } | null = {
    metal: 10_000,
    crystal: 10_000,
    deuterium: 0,
  },
  setVault = vi.fn(),
  reload = vi.fn(),
) {
  const client = createApi(fakeFetch(routes));
  render(
    <VaultContext.Provider
      value={{ vault: null, amounts, loading: false, error: null, setVault, reload }}
    >
      <BuildingsPage client={client} />
    </VaultContext.Provider>,
  );
  return { setVault, reload };
}

describe("BuildingsPage", () => {
  it("renders the buildings for the planet in the route", async () => {
    renderPage({ [`GET /planets/${homeworld.id}/buildings`]: { status: 200, body: buildings } });

    expect(await screen.findByText("Metal mine")).toBeTruthy();
  });

  it("reports an upgrade's vault to the shared vault context", async () => {
    const { setVault } = renderPage({
      [`GET /planets/${homeworld.id}/buildings`]: { status: 200, body: buildings },
      [`POST /planets/${homeworld.id}/buildings/metal_mine/upgrade`]: { status: 200, body: buildingUpgrade },
    });
    await screen.findByText("Metal mine");

    fireEvent.click(screen.getByRole("button", { name: "Upgrade Metal mine" }));

    await waitFor(() => expect(setVault).toHaveBeenCalledWith(buildingUpgrade.vault));
  });
});
