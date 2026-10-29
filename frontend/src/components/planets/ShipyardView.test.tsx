import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ShipyardView } from "@/components/planets/ShipyardView";
import {
  fakeFetch,
  homeworld,
  shipOrderResult,
  shipyard,
  shipyardAfterOrderComplete,
  shipyardOrdering,
  shipyardOrderingLastShip,
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

const rich = { metal: 10_000_000, crystal: 10_000_000, deuterium: 10_000_000 };
const shipyardRoute = `GET /planets/${homeworld.id}/ships`;
const orderRoute = (kind: string) => `POST /planets/${homeworld.id}/ships/${kind}/order`;

function renderView(
  routes: Parameters<typeof fakeFetch>[0],
  amounts: { metal: number; crystal: number; deuterium: number } | null = rich,
  shipyardLevel = 1,
  onOrdered = vi.fn(),
  seen: Request[] = [],
) {
  const client = createApi(fakeFetch(routes, seen));
  render(
    <ShipyardView
      planetId={homeworld.id}
      client={client}
      amounts={amounts}
      shipyardLevel={shipyardLevel}
      onOrdered={onOrdered}
    />,
  );
  return onOrdered;
}

function row(name: string) {
  const item = screen.getByText(name).closest("li");
  if (!item) {
    throw new Error(`no list item for ${name}`);
  }
  return within(item);
}

describe("ShipyardView", () => {
  it("renders nothing without a selected planet", () => {
    render(
      <ShipyardView
        planetId={null}
        client={createApi(fakeFetch({}))}
        amounts={null}
        shipyardLevel={0}
        onOrdered={vi.fn()}
      />,
    );

    expect(screen.queryByRole("region", { name: "Shipyard" })).toBeNull();
  });

  it("lists the two ships with their names", async () => {
    renderView({ [shipyardRoute]: { status: 200, body: shipyard } });

    const region = await screen.findByRole("region", { name: "Shipyard" });
    expect(within(region).getByText("Small cargo")).toBeTruthy();
    expect(within(region).getByText("Light fighter")).toBeTruthy();
  });

  it("shows the count built and the build time of one ship", async () => {
    renderView({ [shipyardRoute]: { status: 200, body: shipyard } });
    await screen.findByText("Small cargo");

    expect(row("Small cargo").getByText("Built: 0 · 2880s to build")).toBeTruthy();
    expect(row("Light fighter").getByText("Built: 0 · 3600s to build")).toBeTruthy();
  });

  it("shows the cost of one ship, with thousands separators", async () => {
    renderView({ [shipyardRoute]: { status: 200, body: shipyard } });
    await screen.findByText("Small cargo");

    expect(row("Small cargo").getByText("Cost: 2,000 metal, 2,000 crystal")).toBeTruthy();
    expect(row("Light fighter").getByText("Cost: 3,000 metal, 1,000 crystal")).toBeTruthy();
  });

  it("gives each ship an order form with a count of 1 and an Order button", async () => {
    renderView({ [shipyardRoute]: { status: 200, body: shipyard } });
    await screen.findByText("Small cargo");

    for (const name of ["Small cargo", "Light fighter"]) {
      const input = row(name).getByRole("spinbutton", { name: `${name} count` }) as HTMLInputElement;
      expect(input.value).toBe("1");
      const button = row(name).getByRole("button", { name: `Order ${name}` });
      expect(button.textContent).toBe("Order");
    }
  });

  it("disables the order button while the shipyard has level 0", async () => {
    renderView({ [shipyardRoute]: { status: 200, body: shipyard } }, rich, 0);
    await screen.findByText("Small cargo");

    expect(
      (row("Small cargo").getByRole("button", { name: "Order Small cargo" }) as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it("disables the order button when the vault has too little for the cost", async () => {
    renderView(
      { [shipyardRoute]: { status: 200, body: shipyard } },
      { metal: 100, crystal: 100, deuterium: 0 },
    );
    await screen.findByText("Small cargo");

    expect(
      (row("Small cargo").getByRole("button", { name: "Order Small cargo" }) as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it("disables the order button before the amounts are known", async () => {
    renderView({ [shipyardRoute]: { status: 200, body: shipyard } }, null);
    await screen.findByText("Small cargo");

    expect(
      (row("Small cargo").getByRole("button", { name: "Order Small cargo" }) as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it("re-checks affordability against the count the user enters", async () => {
    renderView(
      { [shipyardRoute]: { status: 200, body: shipyard } },
      { metal: 2_000, crystal: 2_000, deuterium: 0 },
    );
    await screen.findByText("Small cargo");

    const input = row("Small cargo").getByRole("spinbutton", { name: "Small cargo count" });
    const button = () => row("Small cargo").getByRole("button", { name: "Order Small cargo" }) as HTMLButtonElement;
    expect(button().disabled).toBe(false);

    fireEvent.change(input, { target: { value: "2" } });
    expect(button().disabled).toBe(true);
  });

  it("disables the order button when the count is 0 or above 1000", async () => {
    renderView({ [shipyardRoute]: { status: 200, body: shipyard } });
    await screen.findByText("Small cargo");

    const input = row("Small cargo").getByRole("spinbutton", { name: "Small cargo count" });
    const button = () => row("Small cargo").getByRole("button", { name: "Order Small cargo" }) as HTMLButtonElement;

    fireEvent.change(input, { target: { value: "0" } });
    expect(button().disabled).toBe(true);

    fireEvent.change(input, { target: { value: "1001" } });
    expect(button().disabled).toBe(true);

    fireEvent.change(input, { target: { value: "1000" } });
    expect(button().disabled).toBe(false);
  });

  it("shows the running order's kind, remaining, and both countdowns", async () => {
    renderView({ [shipyardRoute]: { status: 200, body: shipyardOrdering } });
    await screen.findByText("Small cargo");

    await waitFor(() =>
      expect(row("Small cargo").getByText("Building · 3 left · next 48:00 · all 144:00")).toBeTruthy(),
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(row("Small cargo").getByText("Building · 3 left · next 47:59 · all 143:59")).toBeTruthy();
  });

  it("disables every order button while an order runs, and labels the other button", async () => {
    renderView({ [shipyardRoute]: { status: 200, body: shipyardOrdering } });
    await screen.findByText("Small cargo");

    const ordering = row("Small cargo").getByRole("button", { name: "Order Small cargo" }) as HTMLButtonElement;
    expect(ordering.disabled).toBe(true);
    expect(ordering.textContent).toBe("Order");

    const other = row("Light fighter").getByRole("button", { name: "Order Light fighter" }) as HTMLButtonElement;
    expect(other.disabled).toBe(true);
    expect(other.textContent).toBe("Another order runs");
  });

  it("reads the shipyard again when the countdown to the next ship reaches 0", async () => {
    const seen: Request[] = [];
    renderView(
      {
        [shipyardRoute]: [
          { status: 200, body: shipyardOrderingLastShip },
          { status: 200, body: shipyardAfterOrderComplete },
        ],
      },
      rich,
      1,
      vi.fn(),
      seen,
    );
    await screen.findByText("Small cargo");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_880_000);
    });

    await waitFor(() => expect(row("Small cargo").getByText("Built: 3 · 2880s to build")).toBeTruthy());
    expect(seen.filter((r) => r.method === "GET")).toHaveLength(2);
  });

  it("reports the vault from a 200, and shows the shipyard from the response", async () => {
    const seen: Request[] = [];
    const onOrdered = renderView(
      { [shipyardRoute]: { status: 200, body: shipyard }, [orderRoute("small_cargo")]: { status: 200, body: shipOrderResult } },
      rich,
      1,
      vi.fn(),
      seen,
    );
    await screen.findByText("Small cargo");

    fireEvent.change(row("Small cargo").getByRole("spinbutton", { name: "Small cargo count" }), {
      target: { value: "3" },
    });
    fireEvent.click(row("Small cargo").getByRole("button", { name: "Order Small cargo" }));

    await waitFor(() =>
      expect(row("Small cargo").getByText("Building · 3 left · next 48:00 · all 144:00")).toBeTruthy(),
    );
    expect(onOrdered).toHaveBeenCalledWith(shipOrderResult.vault);
    const body = await seen[1]!.json();
    expect(body).toEqual({ count: 3 });
  });

  it("shows the detail from a 409 response", async () => {
    renderView({
      [shipyardRoute]: { status: 200, body: shipyard },
      [orderRoute("small_cargo")]: { status: 409, body: { detail: "The vault has too little for the cost" } },
    });
    await screen.findByText("Small cargo");

    fireEvent.click(row("Small cargo").getByRole("button", { name: "Order Small cargo" }));

    expect((await screen.findByRole("alert")).textContent).toBe("The vault has too little for the cost");
  });

  it("shows 'This planet was not found.' when the shipyard 404s", async () => {
    renderView({ [shipyardRoute]: { status: 404, body: { detail: "Not found" } } }, null);

    expect((await screen.findByRole("alert")).textContent).toBe("This planet was not found.");
  });

  it("shows 'This planet was not found.' when an order 404s", async () => {
    renderView({
      [shipyardRoute]: { status: 200, body: shipyard },
      [orderRoute("small_cargo")]: { status: 404, body: { detail: "Not found" } },
    });
    await screen.findByText("Small cargo");

    fireEvent.click(row("Small cargo").getByRole("button", { name: "Order Small cargo" }));

    expect((await screen.findByRole("alert")).textContent).toBe("This planet was not found.");
  });

  it("does not read the clock", async () => {
    const dateNow = vi.spyOn(Date, "now");
    renderView({ [shipyardRoute]: { status: 200, body: shipyard } });
    await screen.findByText("Small cargo");

    expect(dateNow).not.toHaveBeenCalled();
  });
});
