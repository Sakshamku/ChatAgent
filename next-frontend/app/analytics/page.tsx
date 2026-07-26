"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Analytics,
  getAnalytics,
  getProgress,
  getSubjectPerformance,
  ProgressDataPoint,
  SubjectPerformance,
} from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

function formatNumber(value: number | null | undefined, digits = 1) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "-";
}

export default function AnalyticsPage() {
  const { token, loading } = useAuth();
  const router = useRouter();
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [progress, setProgress] = useState<ProgressDataPoint[]>([]);
  const [subjects, setSubjects] = useState<SubjectPerformance[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !token) {
      router.replace("/login");
    }
  }, [loading, token, router]);

  useEffect(() => {
    if (!token) return;
    Promise.all([getAnalytics(token), getProgress(token), getSubjectPerformance(token)])
      .then(([analyticsData, progressData, subjectData]) => {
        setAnalytics(analyticsData);
        setProgress(progressData);
        setSubjects(subjectData);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Unable to load analytics"));
  }, [token]);

  const latestProgress = useMemo(() => progress.slice(-5).reverse(), [progress]);

  if (loading || !token) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">Loading analytics...</div>;
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900 dark:bg-zinc-950 dark:text-zinc-100 md:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-600 dark:text-blue-400">
            Analytics
          </p>
          <h1 className="mt-2 text-3xl font-semibold">Performance Dashboard</h1>
        </div>

        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
            {error}
          </div>
        ) : null}

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Stat label="Total Tests" value={analytics?.total_tests ?? 0} suffix="" />
          <Stat label="Average Score" value={formatNumber(analytics?.average_score)} suffix="" />
          <Stat label="Best Score" value={formatNumber(analytics?.best_score)} suffix="" />
          <Stat label="Average Accuracy" value={formatNumber(analytics?.average_accuracy)} suffix="%" />
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <h2 className="text-xl font-semibold">Recent Progress</h2>
            <div className="mt-4 space-y-3">
              {latestProgress.length === 0 ? (
                <p className="text-sm text-slate-500 dark:text-zinc-400">No test history available.</p>
              ) : (
                latestProgress.map((item) => (
                  <div key={`${item.test_name}-${item.attempted_at}`} className="rounded-2xl bg-slate-50 p-4 dark:bg-zinc-950">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium">{item.test_name}</p>
                      <p className="text-sm text-slate-500 dark:text-zinc-400">{item.attempted_at}</p>
                    </div>
                    <p className="mt-2 text-sm text-slate-600 dark:text-zinc-400">
                      Score {formatNumber(item.score)} | Accuracy {formatNumber(item.percentage)}%
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <h2 className="text-xl font-semibold">Subject Performance</h2>
            <div className="mt-4 space-y-3">
              {subjects.length === 0 ? (
                <p className="text-sm text-slate-500 dark:text-zinc-400">No subject stats yet.</p>
              ) : (
                subjects.map((subject) => (
                  <div key={subject.subject} className="space-y-2">
                    <div className="flex items-center justify-between text-sm font-medium">
                      <span>{subject.subject}</span>
                      <span>{formatNumber(subject.average_percentage)}%</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-zinc-800">
                      <div
                        className="h-full rounded-full bg-blue-600"
                        style={{ width: `${Math.min(subject.average_percentage, 100)}%` }}
                      />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function Stat({
  label,
  value,
  suffix = "%",
}: {
  label: string;
  value: number | string;
  suffix?: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <p className="text-sm text-slate-500 dark:text-zinc-400">{label}</p>
      <p className="mt-2 text-2xl font-semibold">
        {value}
        {suffix}
      </p>
    </div>
  );
}
