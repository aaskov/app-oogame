type Route = { status: number; body?: unknown };

export const ada = { id: "6f1c2b9e-0d5a-4c57-9d57-3a1f6f0b8a11", email: "ada@example.com" };

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
