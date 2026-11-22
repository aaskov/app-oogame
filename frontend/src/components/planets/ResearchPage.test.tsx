import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchPage } from "@/components/planets/ResearchPage";
import { buildings, colony, fakeFetch, homeworld, research, researchStartResult } from "@/components/planets/fakeFetch";
import { VaultContext } from "@/hooks/useVault";
import { createApi } from "@/lib/api";
import type { Building } from "@/lib/api";

const { useParams } = vi.hoisted(() => ({ useParams: vi.fn(() => ({ id: homeworld.id })) }));
vi.mock("next/navigation", () => ({ useParams }));

afterEach(cleanup);

// The research lab's level is derived from the buildings (docs/adr/0117),
// like the shipyard's level: the shared `buildings` fixture
// (BuildingsView.test.tsx) predates it and does not include it.
function withResearchLab(level: number): Building[] {
  return [
    ...buildings,
    {
      kind: "research_lab",
      level,
      production_per_hour: 0,
      energy: { produced: 0, used: 0 },
      upgrade_cost: { metal: 200, crystal: 400, deuterium: 200 },
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
  reload = vi.fn(),
) {
  const client = createApi(
    fakeFetch({ "GET /planets": { status: 200, body: [homeworld, colony] }, ...routes }),
  );
  render(
    <VaultContext.Provider value={{ vault: null, amounts, loading: false, error: null, setVault, reload }}>
      <ResearchPage client={client} />
    </VaultContext.Provider>,
  );
  return { setVault, reload };
}

describe("ResearchPage", () => {
  it("derives the research lab level from the buildings, and enables starting", async () => {
    renderPage({
      [`GET /planets/${homeworld.id}/buildings`]: { status: 200, body: withResearchLab(1) },
      "GET /research": { status: 200, body: research },
    });
    await screen.findByText("Energy technology");

    await waitFor(() =>
      expect((screen.getByRole("button", { name: "Start Energy technology" }) as HTMLButtonElement).disabled).toBe(
        false,
      ),
    );
  });

  it("disables starting while the research lab is level 0", async () => {
    renderPage({
      [`GET /planets/${homeworld.id}/buildings`]: { status: 200, body: withResearchLab(0) },
      "GET /research": { status: 200, body: research },
    });
    await screen.findByText("Energy technology");

    expect((screen.getByRole("button", { name: "Start Energy technology" }) as HTMLButtonElement).disabled).toBe(
      true,
    );
  });

  it("reports a start's vault to the shared vault context", async () => {
    const { setVault } = renderPage({
      [`GET /planets/${homeworld.id}/buildings`]: { status: 200, body: withResearchLab(1) },
      "GET /research": { status: 200, body: research },
      [`POST /planets/${homeworld.id}/research/energy_technology/start`]: {
        status: 200,
        body: researchStartResult,
      },
    });
    await screen.findByText("Energy technology");
    await waitFor(() =>
      expect((screen.getByRole("button", { name: "Start Energy technology" }) as HTMLButtonElement).disabled).toBe(
        false,
      ),
    );

    fireEvent.click(screen.getByRole("button", { name: "Start Energy technology" }));

    await waitFor(() => expect(setVault).toHaveBeenCalledWith(researchStartResult.vault));
  });
});
