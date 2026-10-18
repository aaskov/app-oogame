import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/components/auth/AuthProvider";
import { RegisterForm } from "@/components/auth/RegisterForm";
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
      <RegisterForm />
    </AuthProvider>,
  );
}

function fill(email: string, password: string) {
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: email } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
  fireEvent.click(screen.getByRole("button", { name: "Register" }));
}

const passwordMessage = "Password must be 8–128 characters.";

describe("RegisterForm", () => {
  it("has a label for each input", () => {
    renderForm({});

    expect(screen.getByLabelText("Email").getAttribute("type")).toBe("email");
    expect(screen.getByLabelText("Password").getAttribute("type")).toBe("password");
  });

  it("registers, logs the user in, and goes to /", async () => {
    const seen: Request[] = [];
    renderForm(
      {
        "POST /auth/register": { status: 201, body: ada },
        "POST /auth/login": { status: 200, body: ada },
      },
      seen,
    );

    fill("ada@example.com", "correct horse");

    await waitFor(() => expect(push).toHaveBeenCalledWith("/"));
    const request = seen.find((r) => r.url.endsWith("/auth/register"));
    expect(await request?.json()).toEqual({ email: "ada@example.com", password: "correct horse" });
    expect(seen.some((r) => r.url.endsWith("/auth/login"))).toBe(true);
  });

  it("rejects a password under 8 characters before it sends", async () => {
    const seen: Request[] = [];
    renderForm({}, seen);

    fill("ada@example.com", "1234567");

    expect((await screen.findByRole("alert")).textContent).toBe(passwordMessage);
    expect(seen.some((r) => r.method === "POST")).toBe(false);
    expect(push).not.toHaveBeenCalled();
  });

  it("rejects a password over 128 characters before it sends", async () => {
    const seen: Request[] = [];
    renderForm({}, seen);

    fill("ada@example.com", "x".repeat(129));

    expect((await screen.findByRole("alert")).textContent).toBe(passwordMessage);
    expect(seen.some((r) => r.method === "POST")).toBe(false);
  });

  it("accepts passwords of exactly 8 and 128 characters", async () => {
    for (const length of [8, 128]) {
      const seen: Request[] = [];
      renderForm(
        {
          "POST /auth/register": { status: 201, body: ada },
          "POST /auth/login": { status: 200, body: ada },
        },
        seen,
      );

      fill("ada@example.com", "x".repeat(length));

      await waitFor(() => expect(push).toHaveBeenCalledWith("/"));
      cleanup();
      push.mockClear();
    }
  });

  it("shows a message on 409", async () => {
    renderForm({ "POST /auth/register": { status: 409, body: { detail: "Email exists" } } });

    fill("ada@example.com", "correct horse");

    expect((await screen.findByRole("alert")).textContent).toBe(
      "This email is already registered.",
    );
    expect(push).not.toHaveBeenCalled();
  });

  it("shows a message on 422", async () => {
    renderForm({ "POST /auth/register": { status: 422 } });

    fill("not-an-email", "correct horse");

    expect((await screen.findByRole("alert")).textContent).toBe(
      "Enter a valid email and a password of 8–128 characters.",
    );
  });

  it("shows a generic message on another failure", async () => {
    renderForm({ "POST /auth/register": { status: 500 } });

    fill("ada@example.com", "correct horse");

    expect((await screen.findByRole("alert")).textContent).toBe("Something went wrong. Try again.");
  });
});
