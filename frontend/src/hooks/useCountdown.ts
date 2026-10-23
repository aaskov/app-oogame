"use client";

import { useEffect, useRef, useState } from "react";

function format(secondsLeft: number) {
  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

// Counts down to finishesAt, ticking each second, and calls onComplete once
// when it reaches 0. 0, not Date.now(): a render must not read the clock
// (see useVault for why). The real time is set from an effect, so the first
// render, on the server and on the client, always returns null.
export function useCountdown(finishesAt: string | undefined, onComplete: () => void) {
  const [now, setNow] = useState(0);
  const completedFor = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (!finishesAt) {
      return;
    }
    const tick = () => setNow(Date.now());
    const immediate = setTimeout(tick, 0);
    const id = setInterval(tick, 1000);
    return () => {
      clearTimeout(immediate);
      clearInterval(id);
    };
  }, [finishesAt]);

  useEffect(() => {
    if (!finishesAt || now === 0) {
      return;
    }
    if (Date.parse(finishesAt) <= now && completedFor.current !== finishesAt) {
      completedFor.current = finishesAt;
      onComplete();
    }
  }, [finishesAt, now, onComplete]);

  if (!finishesAt || now === 0) {
    return null;
  }
  const secondsLeft = Math.max(0, Math.ceil((Date.parse(finishesAt) - now) / 1000));
  return format(secondsLeft);
}
