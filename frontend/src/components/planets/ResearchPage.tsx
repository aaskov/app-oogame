"use client";

import { useParams } from "next/navigation";

import { ResearchView } from "@/components/planets/ResearchView";
import { useBuildings } from "@/hooks/useBuildings";
import { useVaultContext } from "@/hooks/useVault";
import type { api } from "@/lib/api";

export function ResearchPage({ client }: { client?: typeof api }) {
  const { id } = useParams<{ id: string }>();
  const { amounts, setVault, reload } = useVaultContext();
  const { buildings } = useBuildings(id, client);
  const researchLabLevel = buildings.find((building) => building.kind === "research_lab")?.level ?? 0;

  return (
    <div className="p-4">
      <ResearchView
        planetId={id}
        client={client}
        amounts={amounts}
        researchLabLevel={researchLabLevel}
        onStarted={setVault}
        onCountdownComplete={reload}
      />
    </div>
  );
}
