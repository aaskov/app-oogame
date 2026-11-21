import { Suspense } from "react";

import { ShipyardPage } from "@/components/planets/ShipyardPage";

export default function Page() {
  return (
    <Suspense fallback={null}>
      <ShipyardPage />
    </Suspense>
  );
}
