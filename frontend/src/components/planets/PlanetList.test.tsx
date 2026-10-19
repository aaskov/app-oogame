import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PlanetList } from "@/components/planets/PlanetList";
import { colony, homeworld } from "@/components/planets/fakeFetch";

afterEach(cleanup);

describe("PlanetList", () => {
  it("lists the planets by name", () => {
    render(<PlanetList planets={[homeworld, colony]} selectedId={null} onSelect={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Homeworld" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Colony" })).toBeTruthy();
  });

  it("marks the selected planet", () => {
    render(<PlanetList planets={[homeworld, colony]} selectedId={colony.id} onSelect={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Homeworld" }).getAttribute("aria-pressed")).toBe(
      "false",
    );
    expect(screen.getByRole("button", { name: "Colony" }).getAttribute("aria-pressed")).toBe("true");
  });

  it("calls onSelect with the planet id when clicked", () => {
    const onSelect = vi.fn();
    render(<PlanetList planets={[homeworld, colony]} selectedId={null} onSelect={onSelect} />);

    fireEvent.click(screen.getByRole("button", { name: "Colony" }));

    expect(onSelect).toHaveBeenCalledWith(colony.id);
  });
});
