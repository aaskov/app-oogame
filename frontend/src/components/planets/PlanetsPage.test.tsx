import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PlanetsPage } from "@/components/planets/PlanetsPage";
import { colony, fakeFetch, homeworld, vault } from "@/components/planets/fakeFetch";
import { AuthContext, useAuthState } from "@/hooks/useAuth";
import { createApi } from "@/lib/api";

const { replace } = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));

const ada = { id: "6f1c2b9e-0d5a-4c57-9d57-3a1f6f0b8a11", email: "ada@example.com" };

afterEach(() => {
  cleanup();
  replace.mockClear();
});

function renderPage(routes: Parameters<typeof fakeFetch>[0], seen: Request[] = []) {
  const client = createApi(fakeFetch(routes, seen));
  function Wrapper({ children }: { children: ReactNode }) {
    return <AuthContext.Provider value={useAuthState(client)}>{children}</AuthContext.Provider>;
  }
  render(
    <Wrapper>
      <PlanetsPage client={client} />
    </Wrapper>,
  );
}

describe("PlanetsPage", () => {
  it("sends a user who is not logged in to /login", async () => {
    renderPage({ "GET /auth/me": { status: 401 } });

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });

  it("lists the planets and selects the first one", async () => {
    renderPage({
      "GET /auth/me": { status: 200, body: ada },
      "GET /planets": { status: 200, body: [homeworld, colony] },
      [`GET /planets/${homeworld.id}/vault`]: { status: 200, body: vault },
    });

    expect(await screen.findByRole("button", { name: "Homeworld" })).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Homeworld" }).getAttribute("aria-pressed"),
    ).toBe("true");
    expect(await screen.findByLabelText("Metal")).toHaveProperty("value", "500");
    expect(replace).not.toHaveBeenCalled();
  });

  it("shows the vault of the planet the user selects", async () => {
    renderPage({
      "GET /auth/me": { status: 200, body: ada },
      "GET /planets": { status: 200, body: [homeworld, colony] },
      [`GET /planets/${homeworld.id}/vault`]: { status: 200, body: vault },
      [`GET /planets/${colony.id}/vault`]: {
        status: 200,
        body: { ...vault, planet_id: colony.id, metal: 42 },
      },
    });

    await screen.findByLabelText("Metal");
    fireEvent.click(screen.getByRole("button", { name: "Colony" }));

    await waitFor(() => expect(screen.getByLabelText("Metal")).toHaveProperty("value", "42"));
  });
});
