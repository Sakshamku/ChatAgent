"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "../../contexts/AuthContext";

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && user) {
      window.location.replace("/mock-test-arena");
    }
  }, [loading, user]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in");
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <div className="mx-auto flex min-h-screen max-w-4xl items-center justify-center px-4 py-16">
        <div className="w-full rounded-3xl border border-white/10 bg-slate-900/95 p-10 shadow-2xl shadow-black/20 backdrop-blur">
          <div className="mb-10 text-center">
            <p className="text-sm uppercase tracking-[0.4em] text-sky-300">Student Portal</p>
            <h1 className="mt-4 text-4xl font-semibold">Sign in to access Mock Test Arena</h1>
            <p className="mt-3 text-slate-400">
              Secure access for your mock exams, analytics, and personalized practice.
            </p>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            <label className="block">
              <span className="text-sm font-medium text-slate-200">Email</span>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-sky-500"
              />
            </label>

            <label className="block">
              <span className="text-sm font-medium text-slate-200">Password</span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-sky-500"
              />
            </label>

            {error ? (
              <div className="rounded-2xl bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                {error}
              </div>
            ) : null}

            <button
              type="submit"
              className="w-full rounded-2xl bg-gradient-to-r from-sky-500 to-indigo-500 px-5 py-3 text-sm font-semibold text-white transition hover:brightness-110"
            >
              Sign In
            </button>
          </form>

          <div className="mt-8 text-center text-sm text-slate-400">
            <p>
              New here?{' '}
              <Link href="/signup" className="font-semibold text-slate-100 hover:text-white">
                Create an account
              </Link>
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
