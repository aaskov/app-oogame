import type { Mine, MineUpgrade, Vault } from "@/lib/api";

type Route = { status: number; body?: unknown };

export const homeworld = { id: "b2b7b8d0-6e1a-4c9e-9b8a-9a9e3d9a1a01", name: "Homeworld" };
export const colony = { id: "d1a9b7a0-6e1a-4c9e-9b8a-9a9e3d9a1a02", name: "Colony" };

export const vault: Vault = {
  planet_id: homeworld.id,
  metal: 500,
  crystal: 500,
  deuterium: 0,
  production_per_hour: { metal: 30, crystal: 15, deuterium: 0 },
  energy: { produced: 0, used: 0 },
  calculated_at: "2026-10-19T00:00:00Z",
};

export const mines: Mine[] = [
  {
    kind: "metal_mine",
    level: 0,
    production_per_hour: 0,
    upgrade_cost: { metal: 60, crystal: 15, deuterium: 0 },
  },
  {
    kind: "crystal_mine",
    level: 0,
    production_per_hour: 0,
    upgrade_cost: { metal: 48, crystal: 24, deuterium: 0 },
  },
  {
    kind: "deuterium_synthesizer",
    level: 0,
    production_per_hour: 0,
    upgrade_cost: { metal: 225, crystal: 75, deuterium: 0 },
  },
];

export const mineUpgrade: MineUpgrade = {
  mine: { kind: "metal_mine", level: 1, production_per_hour: 33, upgrade_cost: { metal: 90, crystal: 22, deuterium: 0 } },
  vault: {
    planet_id: homeworld.id,
    metal: 940,
    crystal: 985,
    deuterium: 0,
    production_per_hour: { metal: 63, crystal: 15, deuterium: 0 },
    energy: { produced: 0, used: 0 },
    calculated_at: "2026-10-19T00:00:00Z",
  },
};

export function fakeFetch(routes: Record<string, Route>, seen: Request[] = []) {
  return async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = new Request(input, init);
    seen.push(request);
    const route = routes[`${request.method} ${new URL(request.url).pathname}`];
    if (!route) {
      return new Response(null, { status: 404 });
    }
    return new Response(route.body === undefined ? null : JSON.stringify(route.body), {
      status: route.status,
      headers: { "Content-Type": "application/json" },
    });
  };
}
