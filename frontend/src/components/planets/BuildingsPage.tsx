"use client";

import { useParams } from "next/navigation";

import { BuildingsView } from "@/components/planets/BuildingsView";
import { useVaultContext } from "@/hooks/useVault";
import type { api } from "@/lib/api";

export function BuildingsPage({ client }: { client?: typeof api }) {
  const { id } = useParams<{ id: string }>();
  const { amounts, setVault, reload } = useVaultContext();

  return (
    <div className="p-4">
      <BuildingsView
        planetId={id}
        client={client}
        amounts={amounts}
        onUpgraded={setVault}
        onCountdownComplete={reload}
      />
    </div>
  );
}
