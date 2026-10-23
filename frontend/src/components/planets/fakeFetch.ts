import type { Building, BuildingUpgrade, Vault } from "@/lib/api";

type Reply = { status: number; body?: unknown };
type Route = Reply | Reply[];

export const homeworld = { id: "b2b7b8d0-6e1a-4c9e-9b8a-9a9e3d9a1a01", name: "Homeworld" };
export const colony = { id: "d1a9b7a0-6e1a-4c9e-9b8a-9a9e3d9a1a02", name: "Colony" };

export const vault: Vault = {
  planet_id: homeworld.id,
  metal: 500,
  crystal: 500,
  deuterium: 0,
  production_per_hour: { metal: 30, crystal: 15, deuterium: 0 },
  energy: { produced: 22, used: 22 },
  capacity: { metal: 10000, crystal: 10000, deuterium: 10000 },
  calculated_at: "2026-10-19T00:00:00Z",
};

export const buildings: Building[] = [
  {
    kind: "metal_mine",
    level: 1,
    production_per_hour: 33,
    energy: { produced: 0, used: 11 },
    upgrade_cost: { metal: 90, crystal: 22, deuterium: 0 },
  },
  {
    kind: "crystal_mine",
    level: 1,
    production_per_hour: 22,
    energy: { produced: 0, used: 11 },
    upgrade_cost: { metal: 72, crystal: 36, deuterium: 0 },
  },
  {
    kind: "deuterium_synthesizer",
    level: 0,
    production_per_hour: 0,
    energy: { produced: 0, used: 0 },
    upgrade_cost: { metal: 225, crystal: 75, deuterium: 0 },
  },
  {
    kind: "solar_plant",
    level: 1,
    production_per_hour: 0,
    energy: { produced: 22, used: 0 },
    upgrade_cost: { metal: 1_125, crystal: 45, deuterium: 0 },
  },
  {
    kind: "metal_storage",
    level: 0,
    production_per_hour: 0,
    energy: { produced: 0, used: 0 },
    upgrade_cost: { metal: 1000, crystal: 0, deuterium: 0 },
  },
  {
    kind: "crystal_storage",
    level: 0,
    production_per_hour: 0,
    energy: { produced: 0, used: 0 },
    upgrade_cost: { metal: 1000, crystal: 500, deuterium: 0 },
  },
  {
    kind: "deuterium_tank",
    level: 0,
    production_per_hour: 0,
    energy: { produced: 0, used: 0 },
    upgrade_cost: { metal: 1000, crystal: 1000, deuterium: 0 },
  },
];

// The metal mine goes to level 2. The energy used rises from 22 to 35, so the
// factor falls from 1 to 22 / 35 and the crystal mine makes less after the reload.
export const buildingUpgrade: BuildingUpgrade = {
  building: {
    kind: "metal_mine",
    level: 2,
    production_per_hour: 45,
    energy: { produced: 0, used: 24 },
    upgrade_cost: { metal: 135, crystal: 33, deuterium: 0 },
  },
  vault: {
    planet_id: homeworld.id,
    metal: 410,
    crystal: 478,
    deuterium: 0,
    production_per_hour: { metal: 75, crystal: 28, deuterium: 0 },
    energy: { produced: 22, used: 35 },
    capacity: { metal: 10000, crystal: 10000, deuterium: 10000 },
    calculated_at: "2026-10-19T00:00:00Z",
  },
};

export const buildingsAfterUpgrade: Building[] = [
  buildingUpgrade.building,
  { ...buildings[1], production_per_hour: 13 },
  buildings[2],
  buildings[3],
  buildings[4],
  buildings[5],
  buildings[6],
];

// The metal mine's upgrade to level 2 is running, due 108 seconds after the
// system time the tests set ("2026-10-19T00:00:00Z"), matching the example
// build time of docs/adr/0114.
export const buildingsUpgrading: Building[] = [
  { ...buildings[0], upgrade_finishes_at: "2026-10-19T00:01:48Z" },
  buildings[1],
  buildings[2],
  buildings[3],
  buildings[4],
  buildings[5],
  buildings[6],
];

export function fakeFetch(routes: Record<string, Route>, seen: Request[] = []) {
  return async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = new Request(input, init);
    seen.push(request);
    const entry = routes[`${request.method} ${new URL(request.url).pathname}`];
    if (!entry) {
      return new Response(null, { status: 404 });
    }
    const route = Array.isArray(entry) ? (entry.length > 1 ? entry.shift()! : entry[0]) : entry;
    return new Response(route.body === undefined ? null : JSON.stringify(route.body), {
      status: route.status,
      headers: { "Content-Type": "application/json" },
    });
  };
}
