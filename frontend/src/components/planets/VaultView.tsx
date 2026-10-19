"use client";

import { VaultForm } from "@/components/planets/VaultForm";
import { useVault } from "@/hooks/useVault";
import type { api } from "@/lib/api";

export function VaultView({
  planetId,
  client,
}: {
  planetId: string | null;
  client?: typeof api;
}) {
  const { vault, loading, error, update } = useVault(planetId, client);

  if (!planetId || loading) {
    return null;
  }

  if (error === 404) {
    return (
      <p role="alert" className="text-sm text-red-600">
        This planet was not found.
      </p>
    );
  }

  if (!vault) {
    return null;
  }

  return (
    <section aria-label="Vault" className="flex flex-col gap-6">
      <dl className="grid grid-cols-3 gap-4 text-center">
        <div>
          <dt className="text-sm text-zinc-500">Metal</dt>
          <dd className="text-lg font-semibold">{vault.metal.toLocaleString("en-US")}</dd>
        </div>
        <div>
          <dt className="text-sm text-zinc-500">Crystal</dt>
          <dd className="text-lg font-semibold">{vault.crystal.toLocaleString("en-US")}</dd>
        </div>
        <div>
          <dt className="text-sm text-zinc-500">Deuterium</dt>
          <dd className="text-lg font-semibold">{vault.deuterium.toLocaleString("en-US")}</dd>
        </div>
      </dl>
      <VaultForm vault={vault} onUpdate={update} />
    </section>
  );
}
