"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { useAuth } from "@/hooks/useAuth";

const MIN_PASSWORD = 8;
const MAX_PASSWORD = 128;

function messageFor(status: number) {
  if (status === 409) {
    return "This email is already registered.";
  }
  if (status === 422) {
    return "Enter a valid email and a password of 8–128 characters.";
  }
  return "Something went wrong. Try again.";
}

export function RegisterForm() {
  const { register } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (password.length < MIN_PASSWORD || password.length > MAX_PASSWORD) {
      setError("Password must be 8–128 characters.");
      return;
    }
    setError(null);
    setSubmitting(true);
    const result = await register({ email, password });
    setSubmitting(false);
    if (result.ok) {
      router.push("/");
    } else {
      setError(messageFor(result.status));
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
          className="w-full rounded border border-zinc-400 px-3 py-2 text-base font-normal"
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
          className="w-full rounded border border-zinc-400 px-3 py-2 text-base font-normal"
        />
      </label>
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={submitting}
        className="rounded bg-zinc-900 px-4 py-3 text-base font-medium text-white disabled:opacity-60"
      >
        Register
      </button>
    </form>
  );
}
