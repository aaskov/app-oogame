import { Suspense } from "react";

import { ResearchPage } from "@/components/planets/ResearchPage";

export default function Page() {
  return (
    <Suspense fallback={null}>
      <ResearchPage />
    </Suspense>
  );
}
