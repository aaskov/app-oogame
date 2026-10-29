"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { BuildingsView } from "@/components/planets/BuildingsView";
import { PlanetList } from "@/components/planets/PlanetList";
import { ShipyardView } from "@/components/planets/ShipyardView";
import { VaultView } from "@/components/planets/VaultView";
import { useAuth } from "@/hooks/useAuth";
import { usePlanets } from "@/hooks/usePlanets";
import { useVault } from "@/hooks/useVault";
import type { api, Building } from "@/lib/api";

export function PlanetsPage({ client }: { client?: typeof api }) {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const { planets, loading: planetsLoading } = usePlanets(client);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [autoSelected, setAutoSelected] = useState(false);
  const [shipyardLevel, setShipyardLevel] = useState(0);
  const handleBuildingsChanged = useCallback((buildings: Building[]) => {
    setShipyardLevel(buildings.find((building) => building.kind === "shipyard")?.level ?? 0);
  }, []);
  const {
    vault,
    amounts,
    loading: vaultLoading,
    error: vaultError,
    setVault,
    reload: reloadVault,
  } = useVault(selectedId, client);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [authLoading, user, router]);

  if (!planetsLoading && !autoSelected && planets.length > 0) {
    setAutoSelected(true);
    setSelectedId(planets[0].id);
  }

  if (authLoading || !user) {
    return null;
  }

  return (
    <main className="flex flex-1 flex-col gap-6 p-4">
      <h1 className="text-2xl font-semibold">Planets</h1>
      <PlanetList planets={planets} selectedId={selectedId} onSelect={setSelectedId} />
      <VaultView vault={vault} amounts={amounts} loading={vaultLoading} error={vaultError} />
      <BuildingsView
        planetId={selectedId}
        client={client}
        amounts={amounts}
        onUpgraded={setVault}
        onCountdownComplete={reloadVault}
        onBuildingsChanged={handleBuildingsChanged}
      />
      <ShipyardView
        planetId={selectedId}
        client={client}
        amounts={amounts}
        shipyardLevel={shipyardLevel}
        onOrdered={setVault}
      />
    </main>
  );
}
