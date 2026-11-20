import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ResourceAmount } from "@/components/ui/ResourceAmount";

afterEach(cleanup);

describe("ResourceAmount", () => {
  it("shows the amount and the capacity, with thousands separators", () => {
    render(<ResourceAmount kind="metal" label="Metal" amount={1_500_000} capacity={10_000} />);

    expect(screen.getByText("1,500,000 / 10,000")).toBeTruthy();
  });

  it("marks the amount as Full once it reaches the capacity", () => {
    render(<ResourceAmount kind="crystal" label="Crystal" amount={10_000} capacity={10_000} />);

    expect(screen.getByText("Full")).toBeTruthy();
  });

  it("marks the amount as Full when it is above the capacity", () => {
    render(<ResourceAmount kind="crystal" label="Crystal" amount={15_000} capacity={10_000} />);

    expect(screen.getByText("Full")).toBeTruthy();
  });

  it("does not show Full below the capacity", () => {
    render(<ResourceAmount kind="deuterium" label="Deuterium" amount={5_000} capacity={10_000} />);

    expect(screen.queryByText("Full")).toBeNull();
  });
});
