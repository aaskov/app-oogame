import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MinesView } from "@/components/planets/MinesView";
import { fakeFetch, homeworld, mineUpgrade, mines } from "@/components/planets/fakeFetch";
import { createApi } from "@/lib/api";

afterEach(cleanup);

describe("MinesView", () => {
  it("renders nothing without a selected planet", () => {
    render(
      <MinesView planetId={null} client={createApi(fakeFetch({}))} amounts={null} onUpgraded={vi.fn()} />,
    );

    expect(screen.queryByRole("region", { name: "Mines" })).toBeNull();
  });

  it("lists each mine with its name, level, production, and upgrade cost", async () => {
    const client = createApi(
      fakeFetch({ [`GET /planets/${homeworld.id}/mines`]: { status: 200, body: mines } }),
    );
    render(<MinesView planetId={homeworld.id} client={client} amounts={null} onUpgraded={vi.fn()} />);

    expect(await screen.findByText("Metal mine")).toBeTruthy();
    expect(screen.getByText("Crystal mine")).toBeTruthy();
    expect(screen.getByText("Deuterium synthesizer")).toBeTruthy();
    expect(
      screen.getByText((_, node) => node?.textContent === "Cost: 60 metal, 15 crystal"),
    ).toBeTruthy();
  });

  it("disables the upgrade button while the shown amounts are below the cost", async () => {
    const client = createApi(
      fakeFetch({ [`GET /planets/${homeworld.id}/mines`]: { status: 200, body: mines } }),
    );
    render(
      <MinesView
        planetId={homeworld.id}
        client={client}
        amounts={{ metal: 10, crystal: 10, deuterium: 0 }}
        onUpgraded={vi.fn()}
      />,
    );

    const button = await screen.findByRole("button", { name: "Upgrade Metal mine" });
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });

  it("enables the upgrade button once the shown amounts cover the cost", async () => {
    const client = createApi(
      fakeFetch({ [`GET /planets/${homeworld.id}/mines`]: { status: 200, body: mines } }),
    );
    render(
      <MinesView
        planetId={homeworld.id}
        client={client}
        amounts={{ metal: 1000, crystal: 1000, deuterium: 0 }}
        onUpgraded={vi.fn()}
      />,
    );

    const button = await screen.findByRole("button", { name: "Upgrade Metal mine" });
    expect((button as HTMLButtonElement).disabled).toBe(false);
  });

  it("shows the mine from the response after a 200, and reports the new vault", async () => {
    const onUpgraded = vi.fn();
    const client = createApi(
      fakeFetch({
        [`GET /planets/${homeworld.id}/mines`]: { status: 200, body: mines },
        [`POST /planets/${homeworld.id}/mines/metal_mine/upgrade`]: {
          status: 200,
          body: mineUpgrade,
        },
      }),
    );
    render(
      <MinesView
        planetId={homeworld.id}
        client={client}
        amounts={{ metal: 1000, crystal: 1000, deuterium: 0 }}
        onUpgraded={onUpgraded}
      />,
    );

    const button = await screen.findByRole("button", { name: "Upgrade Metal mine" });
    fireEvent.click(button);

    await waitFor(() =>
      expect(
        screen.getByText((_, node) => node?.textContent === "Level 1 · +33/h"),
      ).toBeTruthy(),
    );
    expect(onUpgraded).toHaveBeenCalledWith(mineUpgrade.vault);
  });

  it("shows 'Not enough resources.' on a 409", async () => {
    const client = createApi(
      fakeFetch({
        [`GET /planets/${homeworld.id}/mines`]: { status: 200, body: mines },
        [`POST /planets/${homeworld.id}/mines/metal_mine/upgrade`]: {
          status: 409,
          body: { detail: "Not enough resources" },
        },
      }),
    );
    render(
      <MinesView
        planetId={homeworld.id}
        client={client}
        amounts={{ metal: 1000, crystal: 1000, deuterium: 0 }}
        onUpgraded={vi.fn()}
      />,
    );

    const button = await screen.findByRole("button", { name: "Upgrade Metal mine" });
    fireEvent.click(button);

    expect((await screen.findByRole("alert")).textContent).toBe("Not enough resources.");
  });

  it("shows 'This planet was not found.' when the mine list 404s", async () => {
    const client = createApi(
      fakeFetch({
        [`GET /planets/${homeworld.id}/mines`]: { status: 404, body: { detail: "Not found" } },
      }),
    );
    render(<MinesView planetId={homeworld.id} client={client} amounts={null} onUpgraded={vi.fn()} />);

    expect((await screen.findByRole("alert")).textContent).toBe("This planet was not found.");
  });

  it("shows 'This planet was not found.' when an upgrade 404s", async () => {
    const client = createApi(
      fakeFetch({
        [`GET /planets/${homeworld.id}/mines`]: { status: 200, body: mines },
        [`POST /planets/${homeworld.id}/mines/metal_mine/upgrade`]: {
          status: 404,
          body: { detail: "Not found" },
        },
      }),
    );
    render(
      <MinesView
        planetId={homeworld.id}
        client={client}
        amounts={{ metal: 1000, crystal: 1000, deuterium: 0 }}
        onUpgraded={vi.fn()}
      />,
    );

    const button = await screen.findByRole("button", { name: "Upgrade Metal mine" });
    fireEvent.click(button);

    expect((await screen.findByRole("alert")).textContent).toBe("This planet was not found.");
  });
});
