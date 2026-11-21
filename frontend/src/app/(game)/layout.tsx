import { Suspense, type ReactNode } from "react";

import { GameFrame } from "./GameFrame";

export default function GameLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={null}>
      <GameFrame>{children}</GameFrame>
    </Suspense>
  );
}
