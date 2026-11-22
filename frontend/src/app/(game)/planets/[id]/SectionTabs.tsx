"use client";

import { Tabs } from "@/components/ui/Tabs";

export function SectionTabs({
  planetId,
  active,
}: {
  planetId: string;
  active: "buildings" | "shipyard" | "research";
}) {
  return (
    <Tabs
      items={[
        {
          label: "Buildings",
          href: `/planets/${planetId}/buildings`,
          isActive: active === "buildings",
        },
        {
          label: "Shipyard",
          href: `/planets/${planetId}/shipyard`,
          isActive: active === "shipyard",
        },
        {
          label: "Research",
          href: `/planets/${planetId}/research`,
          isActive: active === "research",
        },
      ]}
    />
  );
}
