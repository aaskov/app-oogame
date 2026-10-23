import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useCountdown } from "@/hooks/useCountdown";

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(new Date("2026-10-19T00:00:00Z"));
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("useCountdown", () => {
  it("returns null without a finishesAt", () => {
    const { result } = renderHook(() => useCountdown(undefined, vi.fn()));

    expect(result.current).toBeNull();
  });

  it("does not read the clock without a finishesAt", () => {
    const now = vi.spyOn(Date, "now");

    renderHook(() => useCountdown(undefined, vi.fn()));

    expect(now).not.toHaveBeenCalled();
  });

  it("formats the time left as minutes:seconds", async () => {
    const { result } = renderHook(() => useCountdown("2026-10-19T00:01:48Z", vi.fn()));

    await waitFor(() => expect(result.current).toBe("1:48"));
  });

  it("counts down each second", async () => {
    const { result } = renderHook(() => useCountdown("2026-10-19T00:01:48Z", vi.fn()));
    await waitFor(() => expect(result.current).toBe("1:48"));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(result.current).toBe("1:47");
  });

  it("calls onComplete once when the countdown reaches 0", async () => {
    const onComplete = vi.fn();
    const { result } = renderHook(() => useCountdown("2026-10-19T00:00:02Z", onComplete));
    await waitFor(() => expect(result.current).toBe("0:02"));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    expect(onComplete).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it("resets and counts the new time when finishesAt changes", async () => {
    const { result, rerender } = renderHook(({ finishesAt }) => useCountdown(finishesAt, vi.fn()), {
      initialProps: { finishesAt: "2026-10-19T00:00:10Z" as string | undefined },
    });
    await waitFor(() => expect(result.current).toBe("0:10"));

    rerender({ finishesAt: "2026-10-19T00:02:00Z" });

    await waitFor(() => expect(result.current).toBe("2:00"));
  });
});
