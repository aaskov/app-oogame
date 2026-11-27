import type { GalaxySystem, Planet, User } from "@/lib/api";

type Reply = { status: number; body?: unknown };
type Route = Reply | Reply[];

export const ada: User = {
  id: "6f1c2b9e-0d5a-4c57-9d57-3a1f6f0b8a11",
  email: "ada@example.com",
  username: "ada",
};

export const homePlanet: Planet = {
  id: "b2b7b8d0-6e1a-4c9e-9b8a-9a9e3d9a1a01",
  name: "Homeworld",
  coordinates: { galaxy: 1, system: 23, position: 4 },
};

export const galaxySystem: GalaxySystem = {
  galaxy: 1,
  system: 23,
  galaxies: 1,
  systems_per_galaxy: 50,
  positions: [
    { position: 1 },
    { position: 2 },
    { position: 3 },
    { position: 4, planet: { name: "Homeworld", username: "ada" } },
    { position: 5 },
    { position: 6 },
    { position: 7, planet: { name: "Outpost", username: "grace" } },
    { position: 8 },
    { position: 9 },
    { position: 10 },
    { position: 11 },
    { position: 12 },
    { position: 13 },
    { position: 14 },
    { position: 15 },
  ],
};

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
