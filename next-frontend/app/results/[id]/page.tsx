"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getTestResultById, TestResult } from "@/lib/api";
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

export default function ResultDetailPage() {
  const { token, loading } = useAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const [result, setResult] = useState<TestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const resultId = params?.id;

  useEffect(() => {
    if (!loading && !token) {
      router.replace("/login");
    }
  }, [loading, token, router]);

  useEffect(() => {
    if (!token || !resultId) return;
    getTestResultById(resultId, token)
      .then(setResult)
      .catch((err) => setError(err instanceof Error ? err.message : "Unable to load test result"));
  }, [token, resultId]);

  if (loading || !token || !resultId) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">Loading result...</div>;
  }

  if (!result) {
    return (
      <main className="min-h-screen bg-slate-50 px-4 py-8 dark:bg-zinc-950">
        <div className="mx-auto max-w-4xl">
          <button type="button" onClick={() => router.back()} className="mb-4 text-sm font-medium text-blue-600">
            Back
          </button>
          {error ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
              {error}
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500 dark:border-zinc-800 dark:bg-zinc-900">
              Loading detailed result...
            </div>
          )}
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900 dark:bg-zinc-950 dark:text-zinc-100 md:px-8">
      <div className="mx-auto max-w-5xl space-y-6">
        <button type="button" onClick={() => router.back()} className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400">
          Back
        </button>

        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
            {error}
          </div>
        ) : null}

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-600 dark:text-blue-400">
            Result Detail
          </p>
          <h1 className="mt-2 text-3xl font-semibold">{result.test_name}</h1>
          <p className="mt-2 text-sm text-slate-500 dark:text-zinc-400">{formatDate(result.attempted_at)}</p>
        </section>

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Stat label="Score" value={`${result.correct_answers}/${result.total_questions}`} />
          <Stat label="Accuracy" value={`${result.percentage.toFixed(1)}%`} />
          <Stat label="Time Taken" value={formatTime(result.time_taken_seconds)} />
          <Stat label="Points" value={result.score.toFixed(2)} />
        </section>

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MiniStat label="Correct" value={result.correct_answers} tone="emerald" />
          <MiniStat label="Wrong" value={result.wrong_answers} tone="rose" />
          <MiniStat label="Unattempted" value={result.unattempted_questions} tone="amber" />
          <MiniStat label="Total" value={result.total_questions} tone="violet" />
        </section>

        {result.subjects?.length ? (
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <h2 className="text-xl font-semibold">Subject-wise Performance</h2>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-zinc-800">
                <thead className="bg-slate-100 text-slate-600 dark:bg-zinc-950 dark:text-zinc-300">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold">Subject</th>
                    <th className="px-4 py-3 text-right font-semibold">Score</th>
                    <th className="px-4 py-3 text-right font-semibold">Correct</th>
                    <th className="px-4 py-3 text-right font-semibold">Wrong</th>
                    <th className="px-4 py-3 text-right font-semibold">Total</th>
                    <th className="px-4 py-3 text-right font-semibold">Accuracy</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-zinc-800">
                  {result.subjects.map((subject) => (
                    <tr key={subject.id}>
                      <td className="px-4 py-3 font-medium">{subject.subject_name}</td>
                      <td className="px-4 py-3 text-right">{subject.score.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right">{subject.correct_answers}</td>
                      <td className="px-4 py-3 text-right">{subject.wrong_answers}</td>
                      <td className="px-4 py-3 text-right">{subject.total_questions}</td>
                      <td className="px-4 py-3 text-right">{subject.percentage.toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}
      </div>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <p className="text-sm text-slate-500 dark:text-zinc-400">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function MiniStat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "emerald" | "rose" | "amber" | "violet";
}) {
  const tones = {
    emerald: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300",
    rose: "bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300",
    amber: "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300",
    violet: "bg-violet-50 text-violet-700 dark:bg-violet-950/40 dark:text-violet-300",
  } as const;

  return (
    <div className={`rounded-2xl p-5 ${tones[tone]}`}>
      <p className="text-sm font-medium">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}
