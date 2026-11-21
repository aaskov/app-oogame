import { Suspense } from "react";

import { HomeworldPage } from "@/components/planets/HomeworldPage";

export default function Page() {
  return (
    <Suspense fallback={null}>
      <HomeworldPage />
    </Suspense>
  );
}
