import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ResourceBar } from "@/app/(game)/planets/[id]/ResourceBar";
import { vault } from "@/components/planets/fakeFetch";

afterEach(cleanup);

describe("ResourceBar", () => {
  it("renders nothing while loading", () => {
    render(<ResourceBar vault={null} amounts={null} loading={true} error={null} />);

    expect(screen.queryByRole("region", { name: "Resources" })).toBeNull();
  });

  it("renders nothing on a 404", () => {
    render(<ResourceBar vault={null} amounts={null} loading={false} error={404} />);

    expect(screen.queryByRole("region", { name: "Resources" })).toBeNull();
  });

  it("shows metal, crystal, and deuterium as amount / capacity", () => {
    render(
      <ResourceBar
        vault={vault}
        amounts={{ metal: 1_500_000, crystal: 2_000, deuterium: 0 }}
        loading={false}
        error={null}
      />,
    );

    expect(screen.getByText("1,500,000 / 10,000")).toBeTruthy();
    expect(screen.getByText("2,000 / 10,000")).toBeTruthy();
    expect(screen.getByText("0 / 10,000")).toBeTruthy();
  });

  it("marks a resource at its capacity as Full", () => {
    render(
      <ResourceBar
        vault={vault}
        amounts={{ metal: 10_000, crystal: 2_000, deuterium: 0 }}
        loading={false}
        error={null}
      />,
    );

    expect(screen.getAllByText("Full").length).toBeGreaterThan(0);
  });

  it("shows energy as produced / used", () => {
    render(
      <ResourceBar
        vault={{ ...vault, energy: { produced: 22, used: 20 } }}
        amounts={{ metal: 500, crystal: 500, deuterium: 0 }}
        loading={false}
        error={null}
      />,
    );

    expect(screen.getByText("22 / 20")).toBeTruthy();
    expect(screen.queryByText("Low")).toBeNull();
  });

  it("marks the energy as Low when used is more than produced", () => {
    render(
      <ResourceBar
        vault={{ ...vault, energy: { produced: 22, used: 24 } }}
        amounts={{ metal: 500, crystal: 500, deuterium: 0 }}
        loading={false}
        error={null}
      />,
    );

    expect(screen.getByText("Low")).toBeTruthy();
  });

  it("uses env(safe-area-inset-bottom) for its bottom padding", () => {
    render(
      <ResourceBar
        vault={vault}
        amounts={{ metal: 500, crystal: 500, deuterium: 0 }}
        loading={false}
        error={null}
      />,
    );

    expect(screen.getByRole("region", { name: "Resources" }).style.paddingBottom).toContain(
      "safe-area-inset-bottom",
    );
  });
});
