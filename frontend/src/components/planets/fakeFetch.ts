type Route = { status: number; body?: unknown };

export const homeworld = { id: "b2b7b8d0-6e1a-4c9e-9b8a-9a9e3d9a1a01", name: "Homeworld" };
export const colony = { id: "d1a9b7a0-6e1a-4c9e-9b8a-9a9e3d9a1a02", name: "Colony" };

export const vault = {
  planet_id: homeworld.id,
  metal: 500,
  crystal: 500,
  deuterium: 0,
  updated_at: "2026-10-19T00:00:00Z",
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
