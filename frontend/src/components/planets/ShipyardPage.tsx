"use client";

import { useParams } from "next/navigation";

import { ShipyardView } from "@/components/planets/ShipyardView";
import { useBuildings } from "@/hooks/useBuildings";
import { useVaultContext } from "@/hooks/useVault";
import type { api } from "@/lib/api";

export function ShipyardPage({ client }: { client?: typeof api }) {
  const { id } = useParams<{ id: string }>();
  const { amounts, setVault } = useVaultContext();
  const { buildings } = useBuildings(id, client);
  const shipyardLevel = buildings.find((building) => building.kind === "shipyard")?.level ?? 0;

  return (
    <div className="p-4">
      <ShipyardView
        planetId={id}
        client={client}
        amounts={amounts}
        shipyardLevel={shipyardLevel}
        onOrdered={setVault}
      />
    </div>
  );
}
