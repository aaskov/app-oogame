"use client";

import { useAuthRedirect } from "@/hooks/useAuthRedirect";

export default function Home() {
  useAuthRedirect();
  return null;
}
