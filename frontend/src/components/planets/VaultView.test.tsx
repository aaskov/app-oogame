import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { VaultView } from "@/components/planets/VaultView";
import { vault } from "@/components/planets/fakeFetch";

afterEach(cleanup);

describe("VaultView", () => {
  it("renders nothing while loading", () => {
    render(<VaultView vault={null} amounts={null} loading={true} error={null} />);

    expect(screen.queryByRole("region", { name: "Vault" })).toBeNull();
  });

  it("shows the metal, crystal, and deuterium amounts as amount / capacity", () => {
    render(
      <VaultView
        vault={vault}
        amounts={{ metal: 1_500_000, crystal: 2000, deuterium: 0 }}
        loading={false}
        error={null}
      />,
    );

    expect(screen.getByText("1,500,000 / 10,000")).toBeTruthy();
    expect(screen.getByText("2,000 / 10,000")).toBeTruthy();
    expect(screen.getByText("0 / 10,000")).toBeTruthy();
  });

  it("shows the production per hour next to each amount", () => {
    render(<VaultView vault={vault} amounts={{ metal: 500, crystal: 500, deuterium: 0 }} loading={false} error={null} />);

    expect(screen.getByText("+30/h")).toBeTruthy();
    expect(screen.getByText("+15/h")).toBeTruthy();
  });

  function renderWithEnergy(energy: { produced: number; used: number }) {
    render(
      <VaultView
        vault={{ ...vault, energy }}
        amounts={{ metal: 500, crystal: 500, deuterium: 0 }}
        loading={false}
        error={null}
      />,
    );
  }

  it("shows the energy as produced / used", () => {
    renderWithEnergy({ produced: 22, used: 20 });

    expect(screen.getByText("Energy: 22 / 20")).toBeTruthy();
    expect(screen.queryByText(/Energy is too low/)).toBeNull();
  });

  it("shows the energy with thousands separators", () => {
    renderWithEnergy({ produced: 12_345, used: 1_000 });

    expect(screen.getByText("Energy: 12,345 / 1,000")).toBeTruthy();
  });

  it("shows no warning when the energy used equals the energy produced", () => {
    renderWithEnergy({ produced: 24, used: 24 });

    expect(screen.getByText("Energy: 24 / 24")).toBeTruthy();
    expect(screen.queryByText(/Energy is too low/)).toBeNull();
  });

  it("warns when the energy used is more than produced, with the percent rounded down", () => {
    renderWithEnergy({ produced: 22, used: 24 });

    expect(screen.getByText("Energy: 22 / 24")).toBeTruthy();
    expect(screen.getByText("Energy is too low. Mines produce 91 %.")).toBeTruthy();
  });

  it("rounds the percent down, not to the nearest number", () => {
    renderWithEnergy({ produced: 1, used: 3 });

    expect(screen.getByText("Energy is too low. Mines produce 33 %.")).toBeTruthy();
  });

  it("shows 0 % when no energy is produced", () => {
    renderWithEnergy({ produced: 0, used: 11 });

    expect(screen.getByText("Energy is too low. Mines produce 0 %.")).toBeTruthy();
  });

  it("shows 'This planet was not found.' on a 404", () => {
    render(<VaultView vault={null} amounts={null} loading={false} error={404} />);

    expect(screen.getByRole("alert").textContent).toBe("This planet was not found.");
  });

  it("shows 'Full' mark when a resource reaches its capacity", () => {
    render(
      <VaultView
        vault={vault}
        amounts={{ metal: 10_000, crystal: 5000, deuterium: 0 }}
        loading={false}
        error={null}
      />,
    );

    const metalFull = screen.getAllByText("Full");
    expect(metalFull.length).toBeGreaterThan(0);
  });

  it("shows 'Full' mark when a resource is above capacity", () => {
    render(
      <VaultView
        vault={vault}
        amounts={{ metal: 15_000, crystal: 5000, deuterium: 0 }}
        loading={false}
        error={null}
      />,
    );

    const fullMarks = screen.getAllByText("Full");
    expect(fullMarks.length).toBeGreaterThan(0);
    expect(screen.getByText("15,000 / 10,000")).toBeTruthy();
  });

  it("does not show 'Full' mark when a resource is below capacity", () => {
    render(
      <VaultView
        vault={vault}
        amounts={{ metal: 5000, crystal: 5000, deuterium: 0 }}
        loading={false}
        error={null}
      />,
    );

    expect(screen.queryByText("Full")).toBeNull();
  });
});
