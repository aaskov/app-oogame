import { Suspense, type ReactNode } from "react";

import type { api } from "@/lib/api";
import { PlanetFrame } from "./PlanetFrame";

export default function PlanetLayout({
  children,
  client,
}: {
  children: ReactNode;
  client?: typeof api;
}) {
  return (
    <Suspense fallback={null}>
      <PlanetFrame client={client}>{children}</PlanetFrame>
    </Suspense>
  );
}
