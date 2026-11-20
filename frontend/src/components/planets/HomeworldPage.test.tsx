import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { HomeworldPage } from "@/components/planets/HomeworldPage";
import { colony, fakeFetch, homeworld } from "@/components/planets/fakeFetch";
import { createApi } from "@/lib/api";

afterEach(cleanup);

function renderPage(routes: Parameters<typeof fakeFetch>[0]) {
  render(<HomeworldPage client={createApi(fakeFetch(routes))} />);
}

describe("HomeworldPage", () => {
  it("lists the planets by name", async () => {
    renderPage({ "GET /planets": { status: 200, body: [homeworld, colony] } });

    expect(await screen.findByRole("link", { name: "Homeworld" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Colony" })).toBeTruthy();
  });

  it("links each planet to its buildings page", async () => {
    renderPage({ "GET /planets": { status: 200, body: [homeworld, colony] } });

    expect((await screen.findByRole("link", { name: "Homeworld" })).getAttribute("href")).toBe(
      `/planets/${homeworld.id}/buildings`,
    );
    expect(screen.getByRole("link", { name: "Colony" }).getAttribute("href")).toBe(
      `/planets/${colony.id}/buildings`,
    );
  });

  it("gives each planet a 44 px minimum tap target", async () => {
    renderPage({ "GET /planets": { status: 200, body: [homeworld] } });

    expect((await screen.findByRole("link", { name: "Homeworld" })).className).toContain("min-h-11");
  });
});
