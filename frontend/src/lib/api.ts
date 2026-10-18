import type { components } from "@/types/api";

export type Health = components["schemas"]["Health"];

const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function getHealth(fetcher: typeof fetch = fetch): Promise<Health> {
  const response = await fetcher(`${baseUrl}/health`);
  if (!response.ok) {
    throw new Error(`GET /health failed with status ${response.status}`);
  }
  return (await response.json()) as Health;
}
