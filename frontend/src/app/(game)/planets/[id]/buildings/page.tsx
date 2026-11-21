import { Suspense } from "react";

import { BuildingsPage } from "@/components/planets/BuildingsPage";

export default function Page() {
  return (
    <Suspense fallback={null}>
      <BuildingsPage />
    </Suspense>
  );
}
