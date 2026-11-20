import type { ReactNode } from "react";

import { Header } from "@/components/auth/Header";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <Header />
      {children}
    </>
  );
}
