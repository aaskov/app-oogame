"use client";

import { useAuthRedirect } from "@/hooks/useAuthRedirect";

export default function Page() {
  useAuthRedirect();
  return null;
}
