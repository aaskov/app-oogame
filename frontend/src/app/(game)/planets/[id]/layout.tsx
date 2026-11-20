"use client";

import { useParams, usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useVault, VaultContext } from "@/hooks/useVault";
import type { api } from "@/lib/api";
import { ResourceBar } from "./ResourceBar";
import { SectionTabs } from "./SectionTabs";

export default function PlanetLayout({
  children,
  client,
}: {
  children: ReactNode;
  client?: typeof api;
}) {
  const { id } = useParams<{ id: string }>();
  const pathname = usePathname();
  const vaultState = useVault(id, client);
  const active = pathname.endsWith("/shipyard") ? "shipyard" : "buildings";

  return (
    <VaultContext.Provider value={vaultState}>
      <div className="flex flex-1 flex-col">
        <SectionTabs planetId={id} active={active} />
        <div className="flex-1 pb-24">{children}</div>
        <ResourceBar
          vault={vaultState.vault}
          amounts={vaultState.amounts}
          loading={vaultState.loading}
          error={vaultState.error}
        />
      </div>
    </VaultContext.Provider>
  );
}
