"use client";

import type { Amounts } from "@/hooks/useVault";
import type { Vault } from "@/lib/api";

const LABELS: { key: keyof Amounts; label: string }[] = [
  { key: "metal", label: "Metal" },
  { key: "crystal", label: "Crystal" },
  { key: "deuterium", label: "Deuterium" },
];

export function VaultView({
  vault,
  amounts,
  loading,
  error,
}: {
  vault: Vault | null;
  amounts: Amounts | null;
  loading: boolean;
  error: number | null;
}) {
  if (loading) {
    return null;
  }

  if (error === 404) {
    return (
      <p role="alert" className="text-sm text-red-600">
        This planet was not found.
      </p>
    );
  }

  if (!vault || !amounts) {
    return null;
  }

  const { produced, used } = vault.energy;

  return (
    <section aria-label="Vault" className="flex flex-col gap-6">
      <dl className="grid grid-cols-3 gap-4 text-center">
        {LABELS.map(({ key, label }) => (
          <div key={key}>
            <dt className="text-sm text-zinc-500">{label}</dt>
            <dd className="text-lg font-semibold">{amounts[key].toLocaleString("en-US")}</dd>
            <dd className="text-xs text-zinc-400">
              +{vault.production_per_hour[key].toLocaleString("en-US")}/h
            </dd>
          </div>
        ))}
      </dl>
      <div className="text-center text-sm">
        <p>
          Energy: {produced.toLocaleString("en-US")} / {used.toLocaleString("en-US")}
        </p>
        {used > produced && (
          <p role="status" className="text-red-600">
            Energy is too low. Mines produce {Math.floor((produced * 100) / used)} %.
          </p>
        )}
      </div>
    </section>
  );
}
