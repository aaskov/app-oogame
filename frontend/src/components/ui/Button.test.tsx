import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Button } from "@/components/ui/Button";

afterEach(cleanup);

describe("Button", () => {
  it("renders its label and type=button by default", () => {
    render(<Button>Log out</Button>);

    const button = screen.getByRole("button", { name: "Log out" }) as HTMLButtonElement;
    expect(button.type).toBe("button");
  });

  it("is at least 44x44 px, the minimum tap target", () => {
    render(<Button>Order</Button>);

    const button = screen.getByRole("button", { name: "Order" });
    expect(button.className).toContain("min-h-11");
    expect(button.className).toContain("min-w-11");
  });

  it("calls onClick when clicked", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Upgrade</Button>);

    fireEvent.click(screen.getByRole("button", { name: "Upgrade" }));

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("is disabled when disabled is passed", () => {
    render(<Button disabled>Order</Button>);

    expect((screen.getByRole("button", { name: "Order" }) as HTMLButtonElement).disabled).toBe(true);
  });
});
