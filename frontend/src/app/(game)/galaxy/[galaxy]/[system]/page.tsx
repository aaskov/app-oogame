import { Suspense } from "react";

import { GalaxyPage } from "@/components/galaxy/GalaxyPage";

export default function Page() {
  return (
    <Suspense fallback={null}>
      <GalaxyPage />
    </Suspense>
  );
}
