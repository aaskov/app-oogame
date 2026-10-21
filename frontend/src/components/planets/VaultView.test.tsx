import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { VaultView } from "@/components/planets/VaultView";
import { fakeFetch, homeworld, vault } from "@/components/planets/fakeFetch";
import { createApi } from "@/lib/api";

afterEach(cleanup);

describe("VaultView", () => {
  it("renders nothing without a selected planet", () => {
    render(<VaultView planetId={null} client={createApi(fakeFetch({}))} />);

    expect(screen.queryByRole("region", { name: "Vault" })).toBeNull();
  });

  it("shows the metal, crystal, and deuterium of the selected planet", async () => {
    const client = createApi(
      fakeFetch({
        [`GET /planets/${homeworld.id}/vault`]: {
          status: 200,
          body: { ...vault, metal: 1_500_000, crystal: 2000, deuterium: 0 },
        },
      }),
    );
    render(<VaultView planetId={homeworld.id} client={client} />);

    expect(await screen.findByText("1,500,000")).toBeTruthy();
    expect(screen.getByText("2,000")).toBeTruthy();
    expect(screen.getAllByText("0").length).toBeGreaterThan(0);
  });

  it("shows 'This planet was not found.' on a 404", async () => {
    const client = createApi(
      fakeFetch({
        [`GET /planets/${homeworld.id}/vault`]: { status: 404, body: { detail: "Not found" } },
      }),
    );
    render(<VaultView planetId={homeworld.id} client={client} />);

    expect((await screen.findByRole("alert")).textContent).toBe("This planet was not found.");
  });
});
