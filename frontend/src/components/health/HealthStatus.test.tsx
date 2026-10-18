import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { HealthStatus } from "@/components/health/HealthStatus";

afterEach(cleanup);

describe("HealthStatus", () => {
  it("shows up when the status is ok", () => {
    render(<HealthStatus health={{ status: "ok" }} />);
    expect(screen.getByRole("status").textContent).toBe("Backend is up");
  });

  it("shows down without a health result", () => {
    render(<HealthStatus health={null} />);
    expect(screen.getByRole("status").textContent).toBe("Backend is down");
  });
});
