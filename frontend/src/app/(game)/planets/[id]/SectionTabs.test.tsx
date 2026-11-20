import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { SectionTabs } from "@/app/(game)/planets/[id]/SectionTabs";

afterEach(cleanup);

describe("SectionTabs", () => {
  it("marks Buildings as the open tab on the buildings page", () => {
    render(<SectionTabs planetId="p1" active="buildings" />);

    expect(screen.getByRole("link", { name: "Buildings" }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("link", { name: "Shipyard" }).getAttribute("aria-current")).toBeNull();
  });

  it("marks Shipyard as the open tab on the shipyard page", () => {
    render(<SectionTabs planetId="p1" active="shipyard" />);

    expect(screen.getByRole("link", { name: "Shipyard" }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("link", { name: "Buildings" }).getAttribute("aria-current")).toBeNull();
  });

  it("links each tab to the planet's route", () => {
    render(<SectionTabs planetId="p1" active="buildings" />);

    expect(screen.getByRole("link", { name: "Buildings" }).getAttribute("href")).toBe("/planets/p1/buildings");
    expect(screen.getByRole("link", { name: "Shipyard" }).getAttribute("href")).toBe("/planets/p1/shipyard");
  });
});
