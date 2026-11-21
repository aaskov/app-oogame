import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ResearchView } from "@/components/planets/ResearchView";
import {
  colony,
  fakeFetch,
  homeworld,
  research,
  researchAfterComplete,
  researchRunning,
  researchStartResult,
} from "@/components/planets/fakeFetch";
import { createApi } from "@/lib/api";
import type { Research } from "@/lib/api";

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(new Date("2026-10-19T00:00:00Z"));
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

const rich = { metal: 10_000_000, crystal: 10_000_000, deuterium: 10_000_000 };
const planetsRoute = "GET /planets";
const researchRoute = "GET /research";
const startRoute = (kind: string) => `POST /planets/${homeworld.id}/research/${kind}/start`;

// A research runs for energy technology, but both technologies are already
// available, so starting plasma technology is blocked only by the running
// research, not by a missing required level.
const researchRunningBothAvailable: Research = {
  technologies: [
    { ...research.technologies[0]!, level: 1 },
    { ...research.technologies[1]!, available: true },
  ],
  running: researchRunning.running,
};

function renderView(
  routes: Parameters<typeof fakeFetch>[0],
  amounts: { metal: number; crystal: number; deuterium: number } | null = rich,
  researchLabLevel = 1,
  onStarted = vi.fn(),
  onCountdownComplete = vi.fn(),
  seen: Request[] = [],
) {
  const client = createApi(
    fakeFetch({ [planetsRoute]: { status: 200, body: [homeworld, colony] }, ...routes }, seen),
  );
  render(
    <ResearchView
      planetId={homeworld.id}
      client={client}
      amounts={amounts}
      researchLabLevel={researchLabLevel}
      onStarted={onStarted}
      onCountdownComplete={onCountdownComplete}
    />,
  );
  return { onStarted, onCountdownComplete };
}

function row(name: string) {
  const item = screen.getByText(name).closest("li");
  if (!item) {
    throw new Error(`no list item for ${name}`);
  }
  return within(item);
}

describe("ResearchView", () => {
  it("renders nothing without a selected planet", () => {
    render(
      <ResearchView
        planetId={null}
        client={createApi(fakeFetch({}))}
        amounts={null}
        researchLabLevel={0}
        onStarted={vi.fn()}
        onCountdownComplete={vi.fn()}
      />,
    );

    expect(screen.queryByRole("region", { name: "Research" })).toBeNull();
  });

  it("lists the two technologies with their names", async () => {
    renderView({ [researchRoute]: { status: 200, body: research } });

    const region = await screen.findByRole("region", { name: "Research" });
    expect(within(region).getByText("Energy technology")).toBeTruthy();
    expect(within(region).getByText("Plasma technology")).toBeTruthy();
  });

  it("shows the level and the cost of the next level", async () => {
    renderView({ [researchRoute]: { status: 200, body: research } });
    await screen.findByText("Energy technology");

    expect(row("Energy technology").getByText("Level 0")).toBeTruthy();
    expect(row("Energy technology").getByText("Cost: 0 metal, 800 crystal, 400 deuterium")).toBeTruthy();
  });

  it("enables the start button when nothing blocks it", async () => {
    renderView({ [researchRoute]: { status: 200, body: research } });
    await screen.findByText("Energy technology");

    await waitFor(() =>
      expect(
        (row("Energy technology").getByRole("button", { name: "Start Energy technology" }) as HTMLButtonElement)
          .disabled,
      ).toBe(false),
    );
  });

  it("disables the start button when available is false, with the text 'Needs energy technology 1'", async () => {
    renderView({ [researchRoute]: { status: 200, body: research } });
    await screen.findByText("Plasma technology");

    const button = row("Plasma technology").getByRole("button", {
      name: "Start Plasma technology",
    }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(button.textContent).toBe("Needs energy technology 1");
  });

  it("disables the start button while the research lab has level 0", async () => {
    renderView({ [researchRoute]: { status: 200, body: research } }, rich, 0);
    await screen.findByText("Energy technology");

    expect(
      (row("Energy technology").getByRole("button", { name: "Start Energy technology" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });

  it("disables the start button when the vault has too little for the cost", async () => {
    renderView(
      { [researchRoute]: { status: 200, body: research } },
      { metal: 0, crystal: 100, deuterium: 0 },
    );
    await screen.findByText("Energy technology");

    expect(
      (row("Energy technology").getByRole("button", { name: "Start Energy technology" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });

  it("disables every start button while a research runs, and labels the other button", async () => {
    renderView({ [researchRoute]: { status: 200, body: researchRunningBothAvailable } });
    await screen.findByText("Energy technology");

    const researching = row("Energy technology").getByRole("button", {
      name: "Start Energy technology",
    }) as HTMLButtonElement;
    expect(researching.disabled).toBe(true);
    expect(researching.textContent).toBe("Start");

    const other = row("Plasma technology").getByRole("button", {
      name: "Start Plasma technology",
    }) as HTMLButtonElement;
    expect(other.disabled).toBe(true);
    expect(other.textContent).toBe("Another research runs");
  });

  it("shows the running research's planet and a countdown to finishes_at", async () => {
    renderView({ [researchRoute]: { status: 200, body: researchRunning } });
    await screen.findByText("Energy technology");

    await waitFor(() =>
      expect(row("Energy technology").getByText("Researching on Homeworld · 24:00")).toBeTruthy(),
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(row("Energy technology").getByText("Researching on Homeworld · 23:59")).toBeTruthy();
  });

  it("reads the research and the vault again when the countdown reaches 0", async () => {
    const seen: Request[] = [];
    const shortRunning: Research = {
      technologies: research.technologies,
      running: { kind: "energy_technology", planet_id: homeworld.id, finishes_at: "2026-10-19T00:00:05Z" },
    };
    const { onCountdownComplete } = renderView(
      {
        [researchRoute]: [
          { status: 200, body: shortRunning },
          { status: 200, body: researchAfterComplete },
        ],
      },
      rich,
      1,
      vi.fn(),
      vi.fn(),
      seen,
    );
    await screen.findByText("Energy technology");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    await waitFor(() => expect(row("Energy technology").getByText("Level 1")).toBeTruthy());
    expect(onCountdownComplete).toHaveBeenCalled();
    expect(seen.filter((r) => r.method === "GET" && r.url.endsWith("/research"))).toHaveLength(2);
  });

  it("reports the vault from a 200, and shows the research from the response", async () => {
    const { onStarted } = renderView({
      [researchRoute]: { status: 200, body: research },
      [startRoute("energy_technology")]: { status: 200, body: researchStartResult },
    });
    await screen.findByText("Energy technology");
    await waitFor(() =>
      expect(
        (row("Energy technology").getByRole("button", { name: "Start Energy technology" }) as HTMLButtonElement)
          .disabled,
      ).toBe(false),
    );

    fireEvent.click(row("Energy technology").getByRole("button", { name: "Start Energy technology" }));

    await waitFor(() =>
      expect(row("Energy technology").getByText("Researching on Homeworld · 24:00")).toBeTruthy(),
    );
    expect(onStarted).toHaveBeenCalledWith(researchStartResult.vault);
  });

  it("shows the detail from a 409 response", async () => {
    renderView({
      [researchRoute]: { status: 200, body: research },
      [startRoute("energy_technology")]: {
        status: 409,
        body: { detail: "A research runs for the player" },
      },
    });
    await screen.findByText("Energy technology");

    fireEvent.click(row("Energy technology").getByRole("button", { name: "Start Energy technology" }));

    expect((await screen.findByRole("alert")).textContent).toBe("A research runs for the player");
  });

  it("does not read the clock", async () => {
    const dateNow = vi.spyOn(Date, "now");
    renderView({ [researchRoute]: { status: 200, body: research } });
    await screen.findByText("Energy technology");

    expect(dateNow).not.toHaveBeenCalled();
  });
});
