import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { HomeworldPage } from "@/components/planets/HomeworldPage";
import { colony, fakeFetch, homeworld } from "@/components/planets/fakeFetch";
import { createApi } from "@/lib/api";

afterEach(cleanup);

function renderPage(routes: Parameters<typeof fakeFetch>[0]) {
  render(<HomeworldPage client={createApi(fakeFetch(routes))} />);
}

const homeworldLinkName = `Homeworld [${homeworld.coordinates.galaxy}:${homeworld.coordinates.system}:${homeworld.coordinates.position}]`;
const colonyLinkName = `Colony [${colony.coordinates.galaxy}:${colony.coordinates.system}:${colony.coordinates.position}]`;

describe("HomeworldPage", () => {
  it("lists the planets by name", async () => {
    renderPage({ "GET /planets": { status: 200, body: [homeworld, colony] } });

    expect(await screen.findByRole("link", { name: homeworldLinkName })).toBeTruthy();
    expect(screen.getByRole("link", { name: colonyLinkName })).toBeTruthy();
  });

  it("shows each planet's coordinates as [galaxy:system:position]", async () => {
    renderPage({ "GET /planets": { status: 200, body: [homeworld] } });

    expect((await screen.findByRole("link", { name: homeworldLinkName })).textContent).toContain(
      "[1:23:7]",
    );
  });

  it("links each planet to its buildings page", async () => {
    renderPage({ "GET /planets": { status: 200, body: [homeworld, colony] } });

    expect((await screen.findByRole("link", { name: homeworldLinkName })).getAttribute("href")).toBe(
      `/planets/${homeworld.id}/buildings`,
    );
    expect(screen.getByRole("link", { name: colonyLinkName }).getAttribute("href")).toBe(
      `/planets/${colony.id}/buildings`,
    );
  });

  it("gives each planet a 44 px minimum tap target", async () => {
    renderPage({ "GET /planets": { status: 200, body: [homeworld] } });

    expect((await screen.findByRole("link", { name: homeworldLinkName })).className).toContain(
      "min-h-11",
    );
  });
});
