"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { useAuth } from "@/hooks/useAuth";

const MIN_PASSWORD = 8;
const MAX_PASSWORD = 128;
const USERNAME_PATTERN = /^[A-Za-z0-9_-]{3,20}$/;

function messageFor(status: number, detail?: string) {
  if (status === 409) {
    return detail ?? "This email or username is already registered.";
  }
  if (status === 422) {
    return "Enter a valid email, username, and password of 8–128 characters.";
  }
  return "Something went wrong. Try again.";
}

export function RegisterForm() {
  const { register } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!USERNAME_PATTERN.test(username)) {
      setError("Username must be 3–20 characters of letters, numbers, _, and -.");
      return;
    }
    if (password.length < MIN_PASSWORD || password.length > MAX_PASSWORD) {
      setError("Password must be 8–128 characters.");
      return;
    }
    setError(null);
    setSubmitting(true);
    const result = await register({ email, username, password });
    setSubmitting(false);
    if (result.ok) {
      router.push("/");
    } else {
      setError(messageFor(result.status, result.detail));
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className="flex w-full max-w-sm flex-col gap-4">
      <h1 className="text-2xl font-semibold">Register</h1>
      <label className="flex flex-col gap-1 text-sm font-medium">
        Email
        <input
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="min-h-11 w-full rounded border border-border bg-surface px-3 py-2 text-base font-normal"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium">
        Username
        <input
          type="text"
          autoComplete="username"
          required
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          className="min-h-11 w-full rounded border border-border bg-surface px-3 py-2 text-base font-normal"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium">
        Password
        <input
          type="password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="min-h-11 w-full rounded border border-border bg-surface px-3 py-2 text-base font-normal"
        />
      </label>
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={submitting}
        className="min-h-11 rounded bg-accent px-4 py-3 text-base font-medium text-white disabled:opacity-60"
      >
        Register
      </button>
    </form>
  );
}
