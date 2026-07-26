"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ApiKeyManager from "@/components/ApiKeyManager";
import { useAuth } from "@/contexts/AuthContext";

export default function SettingsPage() {
  const { token, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !token) {
      router.replace("/login");
    }
  }, [loading, router, token]);

  if (loading || !token) {
    return null;
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10 dark:bg-zinc-950">
      <div className="mx-auto max-w-5xl">
        <div className="mb-6 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-600 dark:text-blue-400">
                AI Settings
              </p>
              <h1 className="mt-2 text-3xl font-semibold text-slate-900 dark:text-zinc-100">
                Connect your Mistral account
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600 dark:text-zinc-400">
                Your chatbot will use your own Mistral API key for every request. The key is encrypted before it is stored and never exposed in full.
              </p>
            </div>
            <Link
              href="/"
              className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition duration-200 hover:-translate-y-0.5 hover:bg-slate-100 hover:shadow-sm dark:border-zinc-700 dark:bg-zinc-900 dark:text-slate-200 dark:hover:bg-zinc-800"
            >
              <span aria-hidden="true">←</span>
              <span>Back to Home</span>
            </Link>
          </div>
        </div>
        <ApiKeyManager />
      </div>
    </main>
  );
}
