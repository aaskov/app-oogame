import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { Tabs } from "@/components/ui/Tabs";

afterEach(cleanup);

const items = [
  { label: "Buildings", href: "/planets/1/buildings", isActive: true },
  { label: "Shipyard", href: "/planets/1/shipyard", isActive: false },
];

describe("Tabs", () => {
  it("renders a link for each tab, with the href", () => {
    render(<Tabs items={items} />);

    expect(screen.getByRole("link", { name: "Buildings" }).getAttribute("href")).toBe(
      "/planets/1/buildings",
    );
    expect(screen.getByRole("link", { name: "Shipyard" }).getAttribute("href")).toBe(
      "/planets/1/shipyard",
    );
  });

  it("marks the open tab with aria-current=page", () => {
    render(<Tabs items={items} />);

    expect(screen.getByRole("link", { name: "Buildings" }).getAttribute("aria-current")).toBe(
      "page",
    );
    expect(screen.getByRole("link", { name: "Shipyard" }).getAttribute("aria-current")).toBeNull();
  });

  it("gives each tab a 44 px minimum tap target", () => {
    render(<Tabs items={items} />);

    expect(screen.getByRole("link", { name: "Buildings" }).className).toContain("min-h-11");
  });
});
