import type { Health } from "@/lib/api";

export function HealthStatus({ health }: { health: Health | null }) {
  const up = health?.status === "ok";
  return (
    <p role="status" className={up ? "text-green-600" : "text-red-600"}>
      {up ? "Backend is up" : "Backend is down"}
    </p>
  );
}
