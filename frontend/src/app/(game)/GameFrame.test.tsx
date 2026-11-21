import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GameFrame } from "@/app/(game)/GameFrame";
import { AuthProvider } from "@/components/auth/AuthProvider";
import { ada, fakeFetch } from "@/components/auth/fakeFetch";
import { createApi } from "@/lib/api";

const { replace, useParams } = vi.hoisted(() => ({
  replace: vi.fn(),
  useParams: vi.fn(() => ({})),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }), useParams }));

afterEach(() => {
  cleanup();
  replace.mockClear();
});

function renderLayout(routes: Parameters<typeof fakeFetch>[0]) {
  render(
    <AuthProvider api={createApi(fakeFetch(routes))}>
      <GameFrame>
        <p>Content</p>
      </GameFrame>
    </AuthProvider>,
  );
}

describe("GameFrame", () => {
  it("sends a user who is not logged in to /login, and renders nothing", async () => {
    renderLayout({ "GET /auth/me": { status: 401 } });

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
    expect(screen.queryByText("Content")).toBeNull();
  });

  it("renders the top bar and the content for a logged-in user", async () => {
    renderLayout({ "GET /auth/me": { status: 200, body: ada }, "GET /planets": { status: 200, body: [] } });

    expect(await screen.findByText("Content")).toBeTruthy();
    expect(screen.getByRole("link", { name: "OOGame" })).toBeTruthy();
    expect(replace).not.toHaveBeenCalled();
  });
});
