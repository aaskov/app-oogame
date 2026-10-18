import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/components/auth/AuthProvider";
import { LoginForm } from "@/components/auth/LoginForm";
import { ada, fakeFetch } from "@/components/auth/fakeFetch";
import { createApi } from "@/lib/api";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

afterEach(() => {
  cleanup();
  push.mockClear();
});

function renderForm(routes: Parameters<typeof fakeFetch>[0], seen: Request[] = []) {
  render(
    <AuthProvider api={createApi(fakeFetch({ "GET /auth/me": { status: 401 }, ...routes }, seen))}>
      <LoginForm />
    </AuthProvider>,
  );
}

function fill(email: string, password: string) {
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: email } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
  fireEvent.click(screen.getByRole("button", { name: "Log in" }));
}

describe("LoginForm", () => {
  it("has a label for each input", () => {
    renderForm({});

    expect(screen.getByLabelText("Email").getAttribute("type")).toBe("email");
    expect(screen.getByLabelText("Password").getAttribute("type")).toBe("password");
  });

  it("sends the credentials and goes to / on success", async () => {
    const seen: Request[] = [];
    renderForm({ "POST /auth/login": { status: 200, body: ada } }, seen);

    fill("ada@example.com", "correct horse");

    await waitFor(() => expect(push).toHaveBeenCalledWith("/"));
    const request = seen.find((r) => r.url.endsWith("/auth/login"));
    expect(await request?.json()).toEqual({ email: "ada@example.com", password: "correct horse" });
  });

  it("shows a message on 401 and stays on the page", async () => {
    renderForm({ "POST /auth/login": { status: 401, body: { detail: "Wrong" } } });

    fill("ada@example.com", "wrong password");

    expect((await screen.findByRole("alert")).textContent).toBe("Wrong email or password.");
    expect(push).not.toHaveBeenCalled();
  });

  it("shows a generic message on another failure", async () => {
    renderForm({ "POST /auth/login": { status: 500 } });

    fill("ada@example.com", "correct horse");

    expect((await screen.findByRole("alert")).textContent).toBe("Something went wrong. Try again.");
  });
});
