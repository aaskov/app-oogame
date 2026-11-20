"use client";

import { ResourceAmount } from "@/components/ui/ResourceAmount";
import type { Amounts } from "@/hooks/useVault";
import type { Vault } from "@/lib/api";

function format(value: number) {
  return value.toLocaleString("en-US");
}

export function ResourceBar({
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
  if (loading || error !== null || !vault || !amounts) {
    return null;
  }

  const { produced, used } = vault.energy;
  const energyTooLow = used > produced;

  return (
    <footer
      role="region"
      aria-label="Resources"
      className="fixed inset-x-0 bottom-0 border-t border-border bg-surface px-2 pt-2 text-foreground"
      style={{ paddingBottom: "max(0.5rem, env(safe-area-inset-bottom))" }}
    >
      <dl className="grid grid-cols-4 gap-2 text-center">
        <ResourceAmount kind="metal" label="Metal" amount={amounts.metal} capacity={vault.capacity.metal} />
        <ResourceAmount
          kind="crystal"
          label="Crystal"
          amount={amounts.crystal}
          capacity={vault.capacity.crystal}
        />
        <ResourceAmount
          kind="deuterium"
          label="Deuterium"
          amount={amounts.deuterium}
          capacity={vault.capacity.deuterium}
        />
        <div className="flex flex-col items-center gap-0.5">
          <dt className="text-xs font-medium text-energy">Energy</dt>
          <dd className="text-sm font-semibold text-foreground">
            {format(produced)} / {format(used)}
          </dd>
          {energyTooLow && (
            <dd role="status" className="text-[10px] font-medium text-danger">
              Low
            </dd>
          )}
        </div>
      </dl>
    </footer>
  );
}
