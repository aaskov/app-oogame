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

  it("shows the metal, crystal, and deuterium amounts with thousands separators", () => {
    render(
      <VaultView
        vault={vault}
        amounts={{ metal: 1_500_000, crystal: 2000, deuterium: 0 }}
        loading={false}
        error={null}
      />,
    );

    expect(screen.getByText("1,500,000")).toBeTruthy();
    expect(screen.getByText("2,000")).toBeTruthy();
    expect(screen.getAllByText("0").length).toBeGreaterThan(0);
  });

  it("shows the production per hour next to each amount", () => {
    render(<VaultView vault={vault} amounts={{ metal: 500, crystal: 500, deuterium: 0 }} loading={false} error={null} />);

    expect(screen.getByText("+30/h")).toBeTruthy();
    expect(screen.getByText("+15/h")).toBeTruthy();
  });

  it("shows 'This planet was not found.' on a 404", () => {
    render(<VaultView vault={null} amounts={null} loading={false} error={404} />);

    expect(screen.getByRole("alert").textContent).toBe("This planet was not found.");
  });
});
