"use client";

import { Tabs } from "@/components/ui/Tabs";

export function SectionTabs({ planetId, active }: { planetId: string; active: "buildings" | "shipyard" }) {
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
      ]}
    />
  );
}
