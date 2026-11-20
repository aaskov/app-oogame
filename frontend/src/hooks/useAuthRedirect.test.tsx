import { cleanup, render, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ada, fakeFetch } from "@/components/auth/fakeFetch";
import { AuthContext, useAuthState } from "@/hooks/useAuth";
import { useAuthRedirect } from "@/hooks/useAuthRedirect";
import { createApi } from "@/lib/api";

const { replace } = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));

afterEach(() => {
  cleanup();
  replace.mockClear();
});

function Probe() {
  useAuthRedirect();
  return null;
}

function renderProbe(routes: Parameters<typeof fakeFetch>[0]) {
  const client = createApi(fakeFetch(routes));
  function Wrapper({ children }: { children: ReactNode }) {
    return <AuthContext.Provider value={useAuthState(client)}>{children}</AuthContext.Provider>;
  }
  render(
    <Wrapper>
      <Probe />
    </Wrapper>,
  );
}

describe("useAuthRedirect", () => {
  it("does not redirect while the user is loading", () => {
    renderProbe({ "GET /auth/me": { status: 200, body: ada } });

    expect(replace).not.toHaveBeenCalled();
  });

  it("sends a logged-in player to /homeworld", async () => {
    renderProbe({ "GET /auth/me": { status: 200, body: ada } });

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/homeworld"));
  });

  it("sends a player without a session to /login", async () => {
    renderProbe({ "GET /auth/me": { status: 401 } });

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });
});
