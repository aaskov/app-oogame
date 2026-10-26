/**
 * The typed API client (docs/adr/0105). Architect-owned (CODEOWNERS).
 *
 * The types come from contracts/openapi.yaml (src/types/api.ts). Use it as
 * api.GET("/auth/me") or api.POST("/auth/login", { body }). The browser sends
 * the httpOnly session cookie with each request.
 */
import createClient from "openapi-fetch";

import type { components, paths } from "@/types/api";

export type Health = components["schemas"]["Health"];
export type User = components["schemas"]["User"];
export type Credentials = components["schemas"]["Credentials"];
export type Planet = components["schemas"]["Planet"];
export type Vault = components["schemas"]["Vault"];
export type Resources = components["schemas"]["Resources"];
export type Amount = components["schemas"]["Amount"];
export type BuildingKind = components["schemas"]["BuildingKind"];
export type Building = components["schemas"]["Building"];
export type BuildingUpgrade = components["schemas"]["BuildingUpgrade"];
export type ShipKind = components["schemas"]["ShipKind"];
export type Ship = components["schemas"]["Ship"];
export type ShipOrder = components["schemas"]["ShipOrder"];
export type Shipyard = components["schemas"]["Shipyard"];
export type ShipOrderRequest = components["schemas"]["ShipOrderRequest"];
export type ShipOrderResult = components["schemas"]["ShipOrderResult"];
export type Energy = components["schemas"]["Energy"];
export type ApiError = components["schemas"]["Error"];

export const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function createApi(fetcher: typeof fetch = globalThis.fetch) {
  return createClient<paths>({ baseUrl, credentials: "include", fetch: fetcher });
}

export const api = createApi();

export async function getHealth(client = api): Promise<Health> {
  const { data, response } = await client.GET("/health");
  if (!data) {
    throw new Error(`GET /health failed with status ${response.status}`);
  }
  return data;
}
