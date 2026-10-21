"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { MinesView } from "@/components/planets/MinesView";
import { PlanetList } from "@/components/planets/PlanetList";
import { VaultView } from "@/components/planets/VaultView";
import { useAuth } from "@/hooks/useAuth";
import { usePlanets } from "@/hooks/usePlanets";
import { useVault } from "@/hooks/useVault";
import type { api } from "@/lib/api";

export function PlanetsPage({ client }: { client?: typeof api }) {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const { planets, loading: planetsLoading } = usePlanets(client);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [autoSelected, setAutoSelected] = useState(false);
  const {
    vault,
    amounts,
    loading: vaultLoading,
    error: vaultError,
    setVault,
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
      <MinesView planetId={selectedId} client={client} amounts={amounts} onUpgraded={setVault} />
    </main>
  );
}
