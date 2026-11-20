import type { HTMLAttributes } from "react";

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded border border-border bg-surface p-4 text-foreground ${className}`}
      {...props}
    />
  );
}
