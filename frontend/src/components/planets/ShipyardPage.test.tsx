import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ShipyardPage } from "@/components/planets/ShipyardPage";
import { buildings, fakeFetch, homeworld, shipOrderResult, shipyard } from "@/components/planets/fakeFetch";
import { VaultContext } from "@/hooks/useVault";
import { createApi } from "@/lib/api";
import type { Building } from "@/lib/api";

const { useParams } = vi.hoisted(() => ({ useParams: vi.fn(() => ({ id: homeworld.id })) }));
vi.mock("next/navigation", () => ({ useParams }));

afterEach(cleanup);

// The buildings list also carries the shipyard's own level (docs/adr/0115):
// the shared `buildings` fixture (BuildingsView.test.tsx) predates the
// shipyard and does not include it, so tests that need a level add it here.
function withShipyard(level: number): Building[] {
  return [
    ...buildings,
    {
      kind: "shipyard",
      level,
      production_per_hour: 0,
      energy: { produced: 0, used: 0 },
      upgrade_cost: { metal: 400, crystal: 200, deuterium: 100 },
    },
  ];
}

function renderPage(
  routes: Parameters<typeof fakeFetch>[0],
  amounts: { metal: number; crystal: number; deuterium: number } | null = {
    metal: 10_000_000,
    crystal: 10_000_000,
    deuterium: 10_000_000,
  },
  setVault = vi.fn(),
) {
  const client = createApi(fakeFetch(routes));
  render(
    <VaultContext.Provider
      value={{ vault: null, amounts, loading: false, error: null, setVault, reload: vi.fn() }}
    >
      <ShipyardPage client={client} />
    </VaultContext.Provider>,
  );
  return { setVault };
}

describe("ShipyardPage", () => {
  it("derives the shipyard level from the buildings, and enables ordering", async () => {
    renderPage({
      [`GET /planets/${homeworld.id}/buildings`]: { status: 200, body: withShipyard(1) },
      [`GET /planets/${homeworld.id}/ships`]: { status: 200, body: shipyard },
    });
    await screen.findByText("Small cargo");

    await waitFor(() =>
      expect(
        (screen.getByRole("button", { name: "Order Small cargo" }) as HTMLButtonElement).disabled,
      ).toBe(false),
    );
  });

  it("disables ordering while the shipyard is level 0", async () => {
    renderPage({
      [`GET /planets/${homeworld.id}/buildings`]: { status: 200, body: withShipyard(0) },
      [`GET /planets/${homeworld.id}/ships`]: { status: 200, body: shipyard },
    });
    await screen.findByText("Small cargo");

    expect(
      (screen.getByRole("button", { name: "Order Small cargo" }) as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it("reports an order's vault to the shared vault context", async () => {
    const { setVault } = renderPage({
      [`GET /planets/${homeworld.id}/buildings`]: { status: 200, body: withShipyard(1) },
      [`GET /planets/${homeworld.id}/ships`]: { status: 200, body: shipyard },
      [`POST /planets/${homeworld.id}/ships/small_cargo/order`]: { status: 200, body: shipOrderResult },
    });
    await screen.findByText("Small cargo");
    await waitFor(() =>
      expect(
        (screen.getByRole("button", { name: "Order Small cargo" }) as HTMLButtonElement).disabled,
      ).toBe(false),
    );

    fireEvent.click(screen.getByRole("button", { name: "Order Small cargo" }));

    await waitFor(() => expect(setVault).toHaveBeenCalledWith(shipOrderResult.vault));
  });
});
