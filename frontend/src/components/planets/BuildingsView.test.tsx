import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BuildingsView } from "@/components/planets/BuildingsView";
import {
  buildingUpgrade,
  buildings,
  buildingsAfterUpgrade,
  buildingsUpgrading,
  fakeFetch,
  homeworld,
} from "@/components/planets/fakeFetch";
import { createApi } from "@/lib/api";

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(new Date("2026-10-19T00:00:00Z"));
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

const rich = { metal: 10_000, crystal: 10_000, deuterium: 0 };
const listRoute = `GET /planets/${homeworld.id}/buildings`;
const upgradeRoute = (kind: string) => `POST /planets/${homeworld.id}/buildings/${kind}/upgrade`;

function renderView(
  routes: Parameters<typeof fakeFetch>[0],
  amounts: { metal: number; crystal: number; deuterium: number } | null = rich,
  onUpgraded = vi.fn(),
  seen: Request[] = [],
  onCountdownComplete = vi.fn(),
) {
  const client = createApi(fakeFetch(routes, seen));
  render(
    <BuildingsView
      planetId={homeworld.id}
      client={client}
      amounts={amounts}
      onUpgraded={onUpgraded}
      onCountdownComplete={onCountdownComplete}
    />,
  );
  return onUpgraded;
}

function row(name: string) {
  const item = screen.getByText(name).closest("li");
  if (!item) {
    throw new Error(`no list item for ${name}`);
  }
  return within(item);
}

describe("BuildingsView", () => {
  it("renders nothing without a selected planet", () => {
    render(
      <BuildingsView
        planetId={null}
        client={createApi(fakeFetch({}))}
        amounts={null}
        onUpgraded={vi.fn()}
        onCountdownComplete={vi.fn()}
      />,
    );

    expect(screen.queryByRole("region", { name: "Buildings" })).toBeNull();
  });

  it("lists the seven buildings in order with their names", async () => {
    renderView({ [listRoute]: { status: 200, body: buildings } });

    const region = await screen.findByRole("region", { name: "Buildings" });
    const names = within(region)
      .getAllByRole("listitem")
      .map((item) => within(item).getAllByText(/./)[0].textContent);
    expect(names).toEqual([
      "Metal mine",
      "Crystal mine",
      "Deuterium synthesizer",
      "Solar plant",
      "Metal storage",
      "Crystal storage",
      "Deuterium tank",
    ]);
  });

  it("shows the level and the production per hour of a mine", async () => {
    renderView({ [listRoute]: { status: 200, body: buildings } });
    await screen.findByText("Metal mine");

    expect(row("Metal mine").getByText("Level 1 · +33/h")).toBeTruthy();
    expect(row("Crystal mine").getByText("Level 1 · +22/h")).toBeTruthy();
  });

  it("shows no production for the solar plant", async () => {
    renderView({ [listRoute]: { status: 200, body: buildings } });
    await screen.findByText("Solar plant");

    expect(row("Solar plant").getByText("Level 1")).toBeTruthy();
    expect(row("Solar plant").queryByText(/\/h/)).toBeNull();
  });

  it("shows the energy a mine uses and the energy the solar plant makes", async () => {
    renderView({ [listRoute]: { status: 200, body: buildings } });
    await screen.findByText("Metal mine");

    expect(row("Metal mine").getByText("−11 energy")).toBeTruthy();
    expect(row("Solar plant").getByText("+22 energy")).toBeTruthy();
    expect(row("Deuterium synthesizer").getByText("0 energy")).toBeTruthy();
  });

  it("shows the cost of the next level, with thousands separators", async () => {
    renderView({ [listRoute]: { status: 200, body: buildings } });
    await screen.findByText("Metal mine");

    expect(row("Metal mine").getByText("Cost: 90 metal, 22 crystal")).toBeTruthy();
    expect(row("Solar plant").getByText("Cost: 1,125 metal, 45 crystal")).toBeTruthy();
  });

  it("gives each building an Upgrade button with a label", async () => {
    renderView({ [listRoute]: { status: 200, body: buildings } });

    for (const name of ["Metal mine", "Crystal mine", "Deuterium synthesizer", "Solar plant"]) {
      const button = await screen.findByRole("button", { name: `Upgrade ${name}` });
      expect(button.textContent).toBe("Upgrade");
    }
  });

  it("disables an Upgrade button while the shown amounts are below the cost", async () => {
    renderView(
      { [listRoute]: { status: 200, body: buildings } },
      { metal: 100, crystal: 40, deuterium: 0 },
    );
    await screen.findByText("Metal mine");

    const disabled = (name: string) =>
      (screen.getByRole("button", { name: `Upgrade ${name}` }) as HTMLButtonElement).disabled;
    expect(disabled("Metal mine")).toBe(false);
    expect(disabled("Crystal mine")).toBe(false);
    expect(disabled("Solar plant")).toBe(true);
  });

  it("disables each Upgrade button before the amounts are known", async () => {
    renderView({ [listRoute]: { status: 200, body: buildings } }, null);
    await screen.findByText("Metal mine");

    expect(
      (screen.getByRole("button", { name: "Upgrade Metal mine" }) as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it("reports the vault from a 200, and reads the list again", async () => {
    const seen: Request[] = [];
    const onUpgraded = renderView(
      {
        [listRoute]: [
          { status: 200, body: buildings },
          { status: 200, body: buildingsAfterUpgrade },
        ],
        [upgradeRoute("metal_mine")]: { status: 200, body: buildingUpgrade },
      },
      rich,
      vi.fn(),
      seen,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Upgrade Metal mine" }));

    await waitFor(() => expect(row("Crystal mine").getByText("Level 1 · +13/h")).toBeTruthy());
    expect(row("Metal mine").getByText("Level 2 · +45/h")).toBeTruthy();
    expect(row("Metal mine").getByText("−24 energy")).toBeTruthy();
    expect(onUpgraded).toHaveBeenCalledWith(buildingUpgrade.vault);
    expect(seen.filter((r) => r.method === "GET")).toHaveLength(2);
  });

  it("shows the detail from a 409 response", async () => {
    renderView({
      [listRoute]: { status: 200, body: buildings },
      [upgradeRoute("metal_mine")]: { status: 409, body: { detail: "Not enough resources" } },
    });

    fireEvent.click(await screen.findByRole("button", { name: "Upgrade Metal mine" }));

    expect((await screen.findByRole("alert")).textContent).toBe("Not enough resources");
  });

  it("shows a different 409 detail when another upgrade runs on the planet", async () => {
    renderView({
      [listRoute]: { status: 200, body: buildings },
      [upgradeRoute("metal_mine")]: {
        status: 409,
        body: { detail: "An upgrade already runs on this planet" },
      },
    });

    fireEvent.click(await screen.findByRole("button", { name: "Upgrade Metal mine" }));

    expect((await screen.findByRole("alert")).textContent).toBe("An upgrade already runs on this planet");
  });

  it("shows 'This planet was not found.' when the list 404s", async () => {
    renderView({ [listRoute]: { status: 404, body: { detail: "Not found" } } }, null);

    expect((await screen.findByRole("alert")).textContent).toBe("This planet was not found.");
  });

  it("shows 'This planet was not found.' when an upgrade 404s", async () => {
    renderView({
      [listRoute]: { status: 200, body: buildings },
      [upgradeRoute("solar_plant")]: { status: 404, body: { detail: "Not found" } },
    });

    fireEvent.click(await screen.findByRole("button", { name: "Upgrade Solar plant" }));

    expect((await screen.findByRole("alert")).textContent).toBe("This planet was not found.");
  });

  it("clears an error message after the next successful upgrade", async () => {
    renderView({
      [listRoute]: { status: 200, body: buildings },
      [upgradeRoute("metal_mine")]: [
        { status: 409, body: { detail: "Not enough resources" } },
        { status: 200, body: buildingUpgrade },
      ],
    });

    fireEvent.click(await screen.findByRole("button", { name: "Upgrade Metal mine" }));
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "Upgrade Metal mine" }));

    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
  });

  it("does not read the clock", async () => {
    const dateNow = vi.spyOn(Date, "now");
    renderView({ [listRoute]: { status: 200, body: buildings } });
    await screen.findByText("Metal mine");

    expect(dateNow).not.toHaveBeenCalled();
  });

  it("shows storage buildings with no production and no energy line", async () => {
    renderView({ [listRoute]: { status: 200, body: buildings } });
    await screen.findByText("Metal storage");

    expect(row("Metal storage").getByText("Level 0")).toBeTruthy();
    expect(row("Metal storage").queryByText(/\/h/)).toBeNull();
    expect(row("Metal storage").queryByText(/energy/)).toBeNull();
    expect(row("Crystal storage").queryByText(/\/h/)).toBeNull();
    expect(row("Crystal storage").queryByText(/energy/)).toBeNull();
    expect(row("Deuterium tank").queryByText(/\/h/)).toBeNull();
    expect(row("Deuterium tank").queryByText(/energy/)).toBeNull();
  });

  it("shows storage building upgrade costs", async () => {
    renderView({ [listRoute]: { status: 200, body: buildings } });
    await screen.findByText("Metal storage");

    expect(row("Metal storage").getByText("Cost: 1,000 metal, 0 crystal")).toBeTruthy();
    expect(row("Crystal storage").getByText("Cost: 1,000 metal, 500 crystal")).toBeTruthy();
    expect(row("Deuterium tank").getByText("Cost: 1,000 metal, 1,000 crystal")).toBeTruthy();
  });

  it("shows the countdown for the upgrading building, counting down each second", async () => {
    renderView({ [listRoute]: { status: 200, body: buildingsUpgrading } });
    await screen.findByText("Metal mine");

    await waitFor(() => expect(row("Metal mine").getByText("Upgrading to level 2 · 1:48")).toBeTruthy());

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(row("Metal mine").getByText("Upgrading to level 2 · 1:47")).toBeTruthy();
  });

  it("turns off every Upgrade button while an upgrade runs, and labels the other buttons", async () => {
    renderView({ [listRoute]: { status: 200, body: buildingsUpgrading } });
    await screen.findByText("Metal mine");

    const upgrading = screen.getByRole("button", { name: "Upgrade Metal mine" }) as HTMLButtonElement;
    expect(upgrading.disabled).toBe(true);
    expect(upgrading.textContent).toBe("Upgrade");

    const other = screen.getByRole("button", { name: "Upgrade Crystal mine" }) as HTMLButtonElement;
    expect(other.disabled).toBe(true);
    expect(other.textContent).toBe("Another upgrade runs");
  });

  it("reads the buildings again, and tells the caller to reload the vault, when the countdown reaches 0", async () => {
    const seen: Request[] = [];
    const onCountdownComplete = vi.fn();
    renderView(
      {
        [listRoute]: [
          { status: 200, body: buildingsUpgrading },
          { status: 200, body: buildingsAfterUpgrade },
        ],
      },
      rich,
      vi.fn(),
      seen,
      onCountdownComplete,
    );
    await screen.findByText("Metal mine");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(108_000);
    });

    await waitFor(() => expect(row("Metal mine").getByText("Level 2 · +45/h")).toBeTruthy());
    expect(onCountdownComplete).toHaveBeenCalledTimes(1);
    expect(seen.filter((r) => r.method === "GET")).toHaveLength(2);
  });
});
