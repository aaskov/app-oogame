import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { VaultForm } from "@/components/planets/VaultForm";
import { vault } from "@/components/planets/fakeFetch";

afterEach(cleanup);

function fill(metal: string, crystal: string, deuterium: string) {
  fireEvent.change(screen.getByLabelText("Metal"), { target: { value: metal } });
  fireEvent.change(screen.getByLabelText("Crystal"), { target: { value: crystal } });
  fireEvent.change(screen.getByLabelText("Deuterium"), { target: { value: deuterium } });
  fireEvent.click(screen.getByRole("button", { name: "Save" }));
}

describe("VaultForm", () => {
  it("has a label for each input, pre-filled with the current values", () => {
    render(<VaultForm vault={vault} onUpdate={vi.fn()} />);

    expect(screen.getByLabelText("Metal")).toHaveProperty("value", "500");
    expect(screen.getByLabelText("Crystal")).toHaveProperty("value", "500");
    expect(screen.getByLabelText("Deuterium")).toHaveProperty("value", "0");
  });

  it("sends whole numbers in range and shows the returned values", async () => {
    const onUpdate = vi.fn().mockResolvedValue({ ok: true });
    render(<VaultForm vault={vault} onUpdate={onUpdate} />);

    fill("1500000", "2000", "9007199254740991");

    await waitFor(() =>
      expect(onUpdate).toHaveBeenCalledWith({
        metal: 1_500_000,
        crystal: 2000,
        deuterium: 9_007_199_254_740_991,
      }),
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("rejects a value above the maximum before it sends", async () => {
    const onUpdate = vi.fn();
    render(<VaultForm vault={vault} onUpdate={onUpdate} />);

    fill("9007199254740992", "0", "0");

    expect((await screen.findByRole("alert")).textContent).toBe("The values are not valid.");
    expect(onUpdate).not.toHaveBeenCalled();
  });

  it("rejects a negative value before it sends", async () => {
    const onUpdate = vi.fn();
    render(<VaultForm vault={vault} onUpdate={onUpdate} />);

    fill("-1", "0", "0");

    expect((await screen.findByRole("alert")).textContent).toBe("The values are not valid.");
    expect(onUpdate).not.toHaveBeenCalled();
  });

  it("rejects a decimal value before it sends", async () => {
    const onUpdate = vi.fn();
    render(<VaultForm vault={vault} onUpdate={onUpdate} />);

    fill("1.5", "0", "0");

    expect((await screen.findByRole("alert")).textContent).toBe("The values are not valid.");
    expect(onUpdate).not.toHaveBeenCalled();
  });

  it("shows a message on a 422 from the server", async () => {
    const onUpdate = vi.fn().mockResolvedValue({ ok: false, status: 422 });
    render(<VaultForm vault={vault} onUpdate={onUpdate} />);

    fill("500", "500", "0");

    expect((await screen.findByRole("alert")).textContent).toBe("The values are not valid.");
  });

  it("shows a generic message on another failure", async () => {
    const onUpdate = vi.fn().mockResolvedValue({ ok: false, status: 0 });
    render(<VaultForm vault={vault} onUpdate={onUpdate} />);

    fill("500", "500", "0");

    expect((await screen.findByRole("alert")).textContent).toBe("Something went wrong. Try again.");
  });

  it("resets its values when the vault is updated", () => {
    const { rerender } = render(<VaultForm vault={vault} onUpdate={vi.fn()} />);

    rerender(
      <VaultForm
        vault={{ ...vault, metal: 42, updated_at: "2026-10-19T01:00:00Z" }}
        onUpdate={vi.fn()}
      />,
    );

    expect(screen.getByLabelText("Metal")).toHaveProperty("value", "42");
  });
});
