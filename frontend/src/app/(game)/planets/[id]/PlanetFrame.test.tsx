import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PlanetFrame } from "@/app/(game)/planets/[id]/PlanetFrame";
import { fakeFetch, homeworld, vault } from "@/components/planets/fakeFetch";
import { createApi } from "@/lib/api";

const { useParams, usePathname } = vi.hoisted(() => ({
  useParams: vi.fn(() => ({ id: homeworld.id })),
  usePathname: vi.fn(() => `/planets/${homeworld.id}/buildings`),
}));
vi.mock("next/navigation", () => ({ useParams, usePathname }));

afterEach(() => {
  cleanup();
  usePathname.mockReturnValue(`/planets/${homeworld.id}/buildings`);
});

function renderLayout(routes: Parameters<typeof fakeFetch>[0]) {
  render(
    <PlanetFrame client={createApi(fakeFetch(routes))}>
      <p>Buildings content</p>
    </PlanetFrame>,
  );
}

describe("PlanetFrame", () => {
  it("renders the tabs, the content, and the resource bar", async () => {
    renderLayout({ [`GET /planets/${homeworld.id}/vault`]: { status: 200, body: vault } });

    expect(screen.getByText("Buildings content")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Buildings" }).getAttribute("aria-current")).toBe("page");
    expect(await screen.findByRole("region", { name: "Resources" })).toBeTruthy();
  });

  it("marks Shipyard as the open tab on the shipyard route", async () => {
    usePathname.mockReturnValue(`/planets/${homeworld.id}/shipyard`);
    renderLayout({ [`GET /planets/${homeworld.id}/vault`]: { status: 200, body: vault } });

    expect(screen.getByRole("link", { name: "Shipyard" }).getAttribute("aria-current")).toBe("page");
  });

  it("marks Research as the open tab on the research route", async () => {
    usePathname.mockReturnValue(`/planets/${homeworld.id}/research`);
    renderLayout({ [`GET /planets/${homeworld.id}/vault`]: { status: 200, body: vault } });

    expect(screen.getByRole("link", { name: "Research" }).getAttribute("aria-current")).toBe("page");
  });
});
