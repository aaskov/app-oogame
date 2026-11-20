import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { Card } from "@/components/ui/Card";

afterEach(cleanup);

describe("Card", () => {
  it("renders its children", () => {
    render(<Card>Homeworld</Card>);

    expect(screen.getByText("Homeworld")).toBeTruthy();
  });

  it("keeps a caller's extra class name", () => {
    render(<Card className="extra-class">Homeworld</Card>);

    expect(screen.getByText("Homeworld").className).toContain("extra-class");
  });
});
