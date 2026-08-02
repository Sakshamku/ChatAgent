"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import AppShell from "../components/AppShell";
import { useAuth } from "@/contexts/AuthContext";

type Mode = "login" | "signup";

export default function Home() {
  const { user, token, loading, apiKeyLoading, apiKeyStatus, login, signup } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user && token) {
      setError(null);
    }
  }, [user, token]);

  useEffect(() => {
    if (!loading && user && token && !apiKeyLoading && !apiKeyStatus?.has_key) {
      router.replace("/settings");
    }
  }, [loading, user, token, apiKeyLoading, apiKeyStatus, router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await signup(fullName, email, password);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500 dark:bg-zinc-950">
        Loading session...
      </div>
    );
  }

  if (user && token && apiKeyLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500 dark:bg-zinc-950">
        Checking API key...
      </div>
    );
  }

  if (user && token && apiKeyStatus?.has_key) {
    return <AppShell />;
  }

  if (user && token && !apiKeyLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500 dark:bg-zinc-950">
        Redirecting to API key setup...
      </div>
    );
  }

  return (
    <main className="flex min-h-screen bg-slate-50 text-slate-900 dark:bg-zinc-950 dark:text-zinc-100">
      <div className="grid flex-1 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="flex items-center justify-center px-4 py-12 lg:px-10">
          <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <div className="mb-6">
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-600 dark:text-blue-400">
                ChatAgent
              </p>
              <h1 className="mt-2 text-3xl font-semibold">
                Sign in to start chatting
              </h1>
              <p className="mt-2 text-sm text-slate-600 dark:text-zinc-400">
                Use your account to access the chat workspace, PDFs, and coding tools.
              </p>
            </div>

            <div className="mb-5 grid grid-cols-2 rounded-2xl bg-slate-100 p-1 dark:bg-zinc-800">
              <button
                type="button"
                onClick={() => setMode("login")}
                className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
                  mode === "login"
                    ? "bg-white text-slate-900 shadow-sm dark:bg-zinc-950 dark:text-zinc-100"
                    : "text-slate-600 dark:text-zinc-300"
                }`}
              >
                Login
              </button>
              <button
                type="button"
                onClick={() => setMode("signup")}
                className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
                  mode === "signup"
                    ? "bg-white text-slate-900 shadow-sm dark:bg-zinc-950 dark:text-zinc-100"
                    : "text-slate-600 dark:text-zinc-300"
                }`}
              >
                Sign up
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === "signup" ? (
                <label className="block space-y-2 text-sm">
                  <span>Full name</span>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 outline-none focus:border-blue-500 dark:border-zinc-700 dark:bg-zinc-950"
                    required={mode === "signup"}
                  />
                </label>
              ) : null}

              <label className="block space-y-2 text-sm">
                <span>Email</span>
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 outline-none focus:border-blue-500 dark:border-zinc-700 dark:bg-zinc-950"
                  required
                />
              </label>

              <label className="block space-y-2 text-sm">
                <span>Password</span>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 outline-none focus:border-blue-500 dark:border-zinc-700 dark:bg-zinc-950"
                  required
                />
              </label>

              {error ? (
                <p className="text-sm text-rose-600 dark:text-rose-300">{error}</p>
              ) : null}

              <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-60"
              >
                {submitting
                  ? mode === "login"
                    ? "Signing in..."
                    : "Creating account..."
                  : mode === "login"
                    ? "Sign in"
                    : "Create account"}
              </button>
            </form>
          </div>
        </section>

        <section className="hidden border-l border-slate-200 bg-slate-950 px-10 py-12 text-slate-100 lg:flex lg:flex-col lg:justify-center dark:border-zinc-800">
          <div className="max-w-xl space-y-6">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">
              Main Workspace
            </p>
            <h2 className="text-4xl font-semibold tracking-tight">
              Chat, Analyze Coding Profiles, Get Roadmap & Recommendations, and practice mock tests in one place.
            </h2>
          </div>
        </section>
      </div>
    </main>
  );
}
