"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { useAuth } from "@/hooks/useAuth";

export function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    const result = await login({ email, password });
    setSubmitting(false);
    if (result.ok) {
      router.push("/");
    } else {
      setError(result.status === 401 ? "Wrong email or password." : "Something went wrong. Try again.");
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className="flex w-full max-w-sm flex-col gap-4">
      <h1 className="text-2xl font-semibold">Log in</h1>
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
          autoComplete="current-password"
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
        Log in
      </button>
    </form>
  );
}
