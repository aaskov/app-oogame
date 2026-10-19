"use client";

import { useState, type FormEvent } from "react";

import type { Vault, VaultUpdate } from "@/lib/api";
import type { VaultResult } from "@/hooks/useVault";

const MAX_AMOUNT = 9_007_199_254_740_991;

function parseAmount(value: string): number | null {
  if (!/^\d+$/.test(value.trim())) {
    return null;
  }
  const amount = Number(value);
  if (!Number.isInteger(amount) || amount < 0 || amount > MAX_AMOUNT) {
    return null;
  }
  return amount;
}

export function VaultForm({
  vault,
  onUpdate,
}: {
  vault: Vault;
  onUpdate: (values: VaultUpdate) => Promise<VaultResult>;
}) {
  const [metal, setMetal] = useState(String(vault.metal));
  const [crystal, setCrystal] = useState(String(vault.crystal));
  const [deuterium, setDeuterium] = useState(String(vault.deuterium));
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [shownVaultKey, setShownVaultKey] = useState(`${vault.planet_id}:${vault.updated_at}`);

  const vaultKey = `${vault.planet_id}:${vault.updated_at}`;
  if (vaultKey !== shownVaultKey) {
    setShownVaultKey(vaultKey);
    setMetal(String(vault.metal));
    setCrystal(String(vault.crystal));
    setDeuterium(String(vault.deuterium));
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const metalValue = parseAmount(metal);
    const crystalValue = parseAmount(crystal);
    const deuteriumValue = parseAmount(deuterium);
    if (metalValue === null || crystalValue === null || deuteriumValue === null) {
      setError("The values are not valid.");
      return;
    }
    setError(null);
    setSubmitting(true);
    const result = await onUpdate({
      metal: metalValue,
      crystal: crystalValue,
      deuterium: deuteriumValue,
    });
    setSubmitting(false);
    if (!result.ok) {
      setError(result.status === 422 ? "The values are not valid." : "Something went wrong. Try again.");
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className="flex w-full max-w-sm flex-col gap-4">
      <label className="flex flex-col gap-1 text-sm font-medium">
        Metal
        <input
          type="text"
          inputMode="numeric"
          value={metal}
          onChange={(event) => setMetal(event.target.value)}
          className="w-full rounded border border-zinc-400 px-3 py-2 text-base font-normal"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium">
        Crystal
        <input
          type="text"
          inputMode="numeric"
          value={crystal}
          onChange={(event) => setCrystal(event.target.value)}
          className="w-full rounded border border-zinc-400 px-3 py-2 text-base font-normal"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium">
        Deuterium
        <input
          type="text"
          inputMode="numeric"
          value={deuterium}
          onChange={(event) => setDeuterium(event.target.value)}
          className="w-full rounded border border-zinc-400 px-3 py-2 text-base font-normal"
        />
      </label>
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={submitting}
        className="rounded bg-zinc-900 px-4 py-3 text-base font-medium text-white disabled:opacity-60"
      >
        Save
      </button>
    </form>
  );
}
