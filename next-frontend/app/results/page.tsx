"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { deleteTestResult, getTestResults, TestResult } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

function formatDate(value: string) {
  return new Date(value).toLocaleString("en-IN", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatTime(seconds: number) {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  return `${hrs > 0 ? `${hrs}h ` : ""}${mins}m ${secs}s`;
}

export default function ResultsPage() {
  const { token, loading } = useAuth();
  const router = useRouter();
  const [results, setResults] = useState<TestResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !token) {
      router.replace("/login");
    }
  }, [loading, token, router]);

  useEffect(() => {
    if (!token) return;
    getTestResults(token)
      .then(setResults)
      .catch((err) => setError(err instanceof Error ? err.message : "Unable to load test results"));
  }, [token]);

  async function handleDelete(resultId: string) {
    if (!token) return;
    setBusyId(resultId);
    setError(null);
    try {
      await deleteTestResult(resultId, token);
      setResults((current) => current.filter((item) => item.id !== resultId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete test result");
    } finally {
      setBusyId(null);
    }
  }

  if (loading || !token) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">Loading results...</div>;
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900 dark:bg-zinc-950 dark:text-zinc-100 md:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-600 dark:text-blue-400">
              Results
            </p>
            <h1 className="mt-2 text-3xl font-semibold">Test Results</h1>
          </div>
          <Link href="/analytics" className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400">
            View analytics
          </Link>
        </div>

        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
            {error}
          </div>
        ) : null}

        {results.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500 dark:border-zinc-800 dark:bg-zinc-900">
            No test results yet. Take a test to see the list here.
          </div>
        ) : (
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-zinc-800">
              <thead className="bg-slate-100 text-slate-600 dark:bg-zinc-950 dark:text-zinc-300">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold">Test Name</th>
                  <th className="px-4 py-3 text-right font-semibold">Score</th>
                  <th className="px-4 py-3 text-right font-semibold">Accuracy</th>
                  <th className="px-4 py-3 text-right font-semibold">Time</th>
                  <th className="px-4 py-3 text-left font-semibold">Date</th>
                  <th className="px-4 py-3 text-right font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-zinc-800">
                {results.map((result) => (
                  <tr key={result.id} className="hover:bg-slate-50 dark:hover:bg-zinc-800/60">
                    <td className="px-4 py-3 font-medium">{result.test_name}</td>
                    <td className="px-4 py-3 text-right">
                      {result.correct_answers}/{result.total_questions}
                    </td>
                    <td className="px-4 py-3 text-right">{result.percentage.toFixed(1)}%</td>
                    <td className="px-4 py-3 text-right">{formatTime(result.time_taken_seconds)}</td>
                    <td className="px-4 py-3">{formatDate(result.attempted_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        <Link
                          href={`/results/${result.id}`}
                          className="rounded-full border border-slate-300 px-3 py-1.5 text-xs font-semibold hover:bg-slate-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
                        >
                          View
                        </Link>
                        <button
                          type="button"
                          onClick={() => handleDelete(result.id)}
                          disabled={busyId === result.id}
                          className="rounded-full border border-rose-300 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-60 dark:border-rose-900/60 dark:text-rose-300 dark:hover:bg-rose-950/30"
                        >
                          {busyId === result.id ? "Deleting..." : "Delete"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
