"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import {
  getProfileOverview,
  getProfileHistory,
  getProfileRecentActivity,
  getProfilePerformanceTrend,
  getProfileAccuracyTrend,
  getProfileSubjectPerformance,
  getProfileStrengthAnalysis,
  ProfileOverview,
  ProgressDataPoint,
  AccuracyTrendPoint,
  SubjectPerformance,
  RecentActivityItem,
  ProfileHistoryResponse,
} from "@/lib/api";

const PAGE_SIZES = [10, 20, 50];

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString("en-IN", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatTime(seconds: number) {
  const safeSeconds = Number.isFinite(seconds) ? seconds : 0;
  const hrs = Math.floor(safeSeconds / 3600);
  const mins = Math.floor((safeSeconds % 3600) / 60);
  const secs = safeSeconds % 60;
  return `${hrs > 0 ? `${hrs}h ` : ""}${mins}m ${secs}s`;
}

function formatNumber(value: number | null | undefined, digits = 1) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "-";
}

function safeNumber(value: number | null | undefined, fallback = 0) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function renderLineChart(
  data: Array<{ label: string; value: number }> = [],
  color: string
) {
  const width = 620;
  const height = 180;
  if (!data.length) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-500">
        No history available
      </div>
    );
  }

  const values = data.map((point) => point.value);
  const maxValue = Math.max(...values, 10);
  const minValue = Math.min(...values, 0);
  const range = maxValue - minValue || 1;
  const points = data.map((point, index) => {
    const x = (index / (data.length - 1 || 1)) * (width - 32) + 16;
    const y = height - 24 - ((point.value - minValue) / range) * (height - 48);
    return `${x},${y}`;
  });
  const pathData = `M${points.join(" L")}`;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-full w-full overflow-visible">
      <defs>
        <linearGradient id="trendGradient" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.35" />
          <stop offset="100%" stopColor={color} stopOpacity="0.06" />
        </linearGradient>
      </defs>
      <path
        d={pathData}
        fill="none"
        stroke={color}
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d={`${pathData} L${width - 16},${height - 16} L16,${height - 16} Z`}
        fill="url(#trendGradient)"
        opacity="0.7"
      />
      {data.map((point, index) => {
        const [cx, cy] = points[index].split(",").map(Number);
        return (
          <circle key={index} cx={cx} cy={cy} r="4" fill={color} stroke="#fff" strokeWidth="2" />
        );
      })}
    </svg>
  );
}

function renderSubjectBars(subjects: SubjectPerformance[]) {
  const maxValue = Math.max(...subjects.map((item) => safeNumber(item.average_percentage)), 100);
  return (
    <div className="space-y-3">
      {subjects.map((subject) => (
        <div key={subject.subject} className="space-y-2">
          <div className="flex items-center justify-between text-sm font-semibold text-slate-800 dark:text-slate-100">
            <span>{subject.subject}</span>
            <span>{formatNumber(subject.average_percentage)}%</span>
          </div>
          <div className="h-3 overflow-hidden rounded-full bg-slate-200 dark:bg-zinc-800">
            <div
              className="h-full rounded-full bg-gradient-to-r from-sky-500 to-blue-600"
              style={{ width: `${Math.min((safeNumber(subject.average_percentage) / maxValue) * 100, 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function ProfileDashboard() {
  const { token, user } = useAuth();
  const [overview, setOverview] = useState<ProfileOverview | null>(null);
  const [history, setHistory] = useState<ProfileHistoryResponse | null>(null);
  const [recentActivity, setRecentActivity] = useState<RecentActivityItem[]>([]);
  const [performanceTrend, setPerformanceTrend] = useState<ProgressDataPoint[]>([]);
  const [accuracyTrend, setAccuracyTrend] = useState<AccuracyTrendPoint[]>([]);
  const [subjectPerformance, setSubjectPerformance] = useState<SubjectPerformance[]>([]);
  const [strengthAnalysis, setStrengthAnalysis] = useState<{
    strongest_subject: string;
    strongest_score: number;
    weakest_subject: string;
    weakest_score: number;
    top_subjects: SubjectPerformance[];
    bottom_subjects: SubjectPerformance[];
  } | null>(null);
  const [filters, setFilters] = useState({
    query: "",
    dateFrom: "",
    dateTo: "",
    minScore: "",
    maxScore: "",
    sortBy: "attempted_at",
    sortDir: "desc",
    page: 1,
    pageSize: 10,
  });
  const [loading, setLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);

  const pageCount = useMemo(() => {
    if (!history) return 0;
    return Math.ceil(history.total / filters.pageSize);
  }, [history, filters.pageSize]);

  useEffect(() => {
    function refresh() {
      setRefreshTick((value) => value + 1);
    }
    function handleStorage(event: StorageEvent) {
      if (event.key === "mock-results-updated-at") refresh();
    }

    window.addEventListener("mock-results-updated", refresh);
    window.addEventListener("storage", handleStorage);
    return () => {
      window.removeEventListener("mock-results-updated", refresh);
      window.removeEventListener("storage", handleStorage);
    };
  }, []);

  useEffect(() => {
    if (!token || !user) return;

    setLoading(true);
    Promise.all([
      getProfileOverview(token),
      getProfileRecentActivity(token),
      getProfilePerformanceTrend(token),
      getProfileAccuracyTrend(token),
      getProfileSubjectPerformance(token),
      getProfileStrengthAnalysis(token),
    ])
      .then(([overviewData, recent, performanceData, accuracyData, subjects, strength]) => {
        setOverview(overviewData);
        setRecentActivity(recent);
        setPerformanceTrend(performanceData);
        setAccuracyTrend(accuracyData);
        setSubjectPerformance(subjects);
        setStrengthAnalysis(strength);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Unable to load dashboard data");
      })
      .finally(() => setLoading(false));
  }, [token, user, refreshTick]);

  useEffect(() => {
    if (!token || !user) return;
    setHistoryLoading(true);
    const params: Record<string, string | number | undefined> = {
      skip: (filters.page - 1) * filters.pageSize,
      limit: filters.pageSize,
      query: filters.query || undefined,
      date_from: filters.dateFrom || undefined,
      date_to: filters.dateTo || undefined,
      min_score: filters.minScore || undefined,
      max_score: filters.maxScore || undefined,
      sort_by: filters.sortBy,
      sort_dir: filters.sortDir,
    };

    getProfileHistory(token, params)
      .then(setHistory)
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Unable to load history");
      })
      .finally(() => setHistoryLoading(false));
  }, [token, user, filters, refreshTick]);

  const historyRows = history?.results ?? [];

  const performanceDataPoints = performanceTrend.map((item) => ({
    label: formatDate(item.attempted_at),
    value: safeNumber(item.score),
  }));

  const accuracyDataPoints = accuracyTrend.map((item) => ({
    label: formatDate(item.attempted_at),
    value: safeNumber(item.accuracy),
  }));

  const topSubjectItems = strengthAnalysis?.top_subjects ?? [];
  const bottomSubjectItems = strengthAnalysis?.bottom_subjects ?? [];

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 text-slate-900 dark:bg-zinc-950 dark:text-slate-100 md:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
          <div className="flex flex-wrap items-center justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-sky-600 dark:text-sky-400">
                Student Profile
              </p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight">
                {user?.full_name ?? "Student"}
              </h1>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                {user?.email}
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-3xl bg-slate-100 p-4 shadow-sm dark:bg-zinc-900">
                <p className="text-sm text-slate-500 dark:text-slate-400">Tests Taken</p>
                <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">
                  {overview?.total_tests ?? "-"}
                </p>
              </div>
              <div className="rounded-3xl bg-slate-100 p-4 shadow-sm dark:bg-zinc-900">
                <p className="text-sm text-slate-500 dark:text-slate-400">Average Score</p>
                <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">
                  {formatNumber(overview?.average_score)}%
                </p>
              </div>
              <div className="rounded-3xl bg-slate-100 p-4 shadow-sm dark:bg-zinc-900">
                <p className="text-sm text-slate-500 dark:text-slate-400">Accuracy</p>
                <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">
                  {formatNumber(overview?.accuracy)}%
                </p>
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="rounded-3xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-900/70 dark:bg-rose-950/40 dark:text-rose-200">
            {error}
          </div>
        )}

        <div className="grid gap-6 xl:grid-cols-[1.4fr_0.8fr]">
          <div className="space-y-6">
            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-500 dark:text-slate-400">
                    Performance Overview
                  </p>
                  <h2 className="mt-2 text-xl font-semibold">Career Metrics</h2>
                </div>
              </div>
              <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {[
                  { label: "Best Score", value: overview?.best_score ?? 0, suffix: "%" },
                  { label: "Lowest Score", value: overview?.lowest_score ?? 0, suffix: "%" },
                  { label: "Total Questions", value: overview?.total_questions ?? 0 },
                  { label: "Total Time", value: overview ? formatTime(overview.total_time_spent_seconds) : "-" },
                ].map((item) => (
                  <div key={item.label} className="rounded-3xl bg-slate-50 p-4 dark:bg-zinc-900">
                    <p className="text-sm text-slate-500 dark:text-slate-400">{item.label}</p>
                    <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-50">
                      {item.value}{item.suffix ?? ""}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            <section className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-500 dark:text-slate-400">
                      Score Trend
                    </p>
                    <h3 className="mt-2 text-lg font-semibold">Progress Over Time</h3>
                  </div>
                  <span className="rounded-full bg-blue-500 px-3 py-1 text-xs font-semibold text-white">
                    {performanceTrend.length} tests
                  </span>
                </div>
                <div className="mt-6 h-[220px]">{renderLineChart(performanceDataPoints, "#2563eb")}</div>
              </div>

              <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-500 dark:text-slate-400">
                      Accuracy Trend
                    </p>
                    <h3 className="mt-2 text-lg font-semibold">Consistency</h3>
                  </div>
                  <span className="rounded-full bg-emerald-500 px-3 py-1 text-xs font-semibold text-white">
                    {accuracyTrend.length} points
                  </span>
                </div>
                <div className="mt-6 h-[220px]">{renderLineChart(accuracyDataPoints, "#059669")}</div>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-500 dark:text-slate-400">
                    Subject Comparison
                  </p>
                  <h3 className="mt-2 text-lg font-semibold">Subject Performance</h3>
                </div>
              </div>
              <div className="mt-6">{renderSubjectBars(subjectPerformance)}</div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-500 dark:text-slate-400">
                    Strength Analysis
                  </p>
                  <h3 className="mt-2 text-lg font-semibold">Strongest & Weakest Subjects</h3>
                </div>
              </div>
              <div className="mt-6 grid gap-4 lg:grid-cols-2">
                <div className="rounded-3xl bg-slate-50 p-5 dark:bg-zinc-900">
                  <p className="text-sm text-slate-500 dark:text-slate-400">Strongest Subject</p>
                  <p className="mt-3 text-2xl font-semibold text-slate-900 dark:text-slate-50">
                    {strengthAnalysis?.strongest_subject ?? "-"}
                  </p>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    {formatNumber(strengthAnalysis?.strongest_score)}% average
                  </p>
                </div>
                <div className="rounded-3xl bg-slate-50 p-5 dark:bg-zinc-900">
                  <p className="text-sm text-slate-500 dark:text-slate-400">Weakest Subject</p>
                  <p className="mt-3 text-2xl font-semibold text-slate-900 dark:text-slate-50">
                    {strengthAnalysis?.weakest_subject ?? "-"}
                  </p>
                  <p className="mt-1 text-sm text-slate-500 dark:text-zinc-400">
                    {formatNumber(strengthAnalysis?.weakest_score)}% average
                  </p>
                </div>
              </div>

              <div className="mt-6 grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">Top 3 Subjects</p>
                  <div className="mt-4 space-y-3">
                    {topSubjectItems.map((subject) => (
                      <div key={subject.subject} className="rounded-3xl bg-slate-100 p-4 dark:bg-zinc-900">
                        <div className="flex items-center justify-between gap-3">
                          <p className="font-medium">{subject.subject}</p>
                          <p className="text-sm text-slate-500 dark:text-slate-400">{formatNumber(subject.average_percentage)}%</p>
                        </div>
                        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                          Best {formatNumber(subject.best_percentage)}% - {subject.total_tests} attempts
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">Bottom 3 Subjects</p>
                  <div className="mt-4 space-y-3">
                    {bottomSubjectItems.map((subject) => (
                      <div key={subject.subject} className="rounded-3xl bg-slate-100 p-4 dark:bg-zinc-900">
                        <div className="flex items-center justify-between gap-3">
                          <p className="font-medium">{subject.subject}</p>
                          <p className="text-sm text-slate-500 dark:text-slate-400">{formatNumber(subject.average_percentage)}%</p>
                        </div>
                        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                          Best {formatNumber(subject.best_percentage)}% - {subject.total_tests} attempts
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </section>
          </div>

          <aside className="space-y-6">
            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500 dark:text-slate-400">
                Recent Activity
              </p>
              <h2 className="mt-2 text-lg font-semibold">Latest Mock Tests</h2>
              <div className="mt-6 space-y-3">
                {recentActivity.length === 0 ? (
                  <p className="text-sm text-slate-500 dark:text-slate-400">No recent test activity yet.</p>
                ) : (
                  recentActivity.map((activity) => (
                    <div key={activity.id} className="rounded-3xl bg-slate-100 p-4 dark:bg-zinc-900">
                      <p className="font-semibold text-slate-900 dark:text-slate-50">{activity.test_name}</p>
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        {activity.attempted_at}
                      </p>
                      <div className="mt-3 flex items-center justify-between gap-3 text-sm">
                        <span className="rounded-full bg-emerald-500 px-3 py-1 text-white">{formatNumber(activity.percentage)}%</span>
                        <Link href={`/results/${activity.id}`} className="text-sky-600 hover:text-sky-500 dark:text-sky-400">
                          View report
                        </Link>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-500 dark:text-slate-400">
                    Test History
                  </p>
                  <h2 className="mt-2 text-lg font-semibold">Recent Attempts</h2>
                </div>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700 dark:bg-zinc-900 dark:text-slate-200">
                  {history?.total ?? 0} records
                </span>
              </div>
              <div className="mt-6 space-y-4">
                <div className="grid gap-3 md:grid-cols-2">
                  <input
                    type="text"
                    placeholder="Search tests"
                    value={filters.query}
                    onChange={(e) => setFilters((prev) => ({ ...prev, query: e.target.value, page: 1 }))}
                    className="rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-slate-100"
                  />
                  <div className="grid gap-3 sm:grid-cols-2">
                    <input
                      type="date"
                      value={filters.dateFrom}
                      onChange={(e) => setFilters((prev) => ({ ...prev, dateFrom: e.target.value, page: 1 }))}
                      className="rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-slate-100"
                    />
                    <input
                      type="date"
                      value={filters.dateTo}
                      onChange={(e) => setFilters((prev) => ({ ...prev, dateTo: e.target.value, page: 1 }))}
                      className="rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-slate-100"
                    />
                  </div>
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  <input
                    type="number"
                    min={0}
                    max={100}
                    placeholder="Min score"
                    value={filters.minScore}
                    onChange={(e) => setFilters((prev) => ({ ...prev, minScore: e.target.value, page: 1 }))}
                    className="rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-slate-100"
                  />
                  <input
                    type="number"
                    min={0}
                    max={100}
                    placeholder="Max score"
                    value={filters.maxScore}
                    onChange={(e) => setFilters((prev) => ({ ...prev, maxScore: e.target.value, page: 1 }))}
                    className="rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-slate-100"
                  />
                  <select
                    value={`${filters.sortBy}|${filters.sortDir}`}
                    onChange={(e) => {
                      const [sortBy, sortDir] = e.target.value.split("|");
                      setFilters((prev) => ({ ...prev, sortBy, sortDir, page: 1 }));
                    }}
                    className="rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-slate-100"
                  >
                    <option value="attempted_at|desc">Newest first</option>
                    <option value="attempted_at|asc">Oldest first</option>
                    <option value="percentage|desc">Highest score</option>
                    <option value="percentage|asc">Lowest score</option>
                  </select>
                </div>

                <div className="overflow-x-auto rounded-3xl border border-slate-200 bg-slate-50 dark:border-zinc-800 dark:bg-zinc-900">
                  <table className="min-w-full divide-y divide-slate-200 text-left text-sm dark:divide-zinc-800">
                    <thead className="bg-slate-100 text-slate-600 dark:bg-zinc-950 dark:text-slate-300">
                      <tr>
                        <th className="px-4 py-3 font-semibold">Test</th>
                        <th className="px-4 py-3 font-semibold">Score</th>
                        <th className="px-4 py-3 font-semibold">Accuracy</th>
                        <th className="px-4 py-3 font-semibold">Time</th>
                        <th className="px-4 py-3 font-semibold">Date</th>
                        <th className="px-4 py-3 font-semibold">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-zinc-800">
                      {historyLoading ? (
                        <tr>
                          <td colSpan={6} className="px-4 py-6 text-center text-slate-500 dark:text-slate-400">
                            Loading history...
                          </td>
                        </tr>
                      ) : historyRows.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="px-4 py-6 text-center text-slate-500 dark:text-slate-400">
                            No matching tests found.
                          </td>
                        </tr>
                      ) : (
                        historyRows.map((item) => (
                          <tr key={item.id} className="hover:bg-slate-100 dark:hover:bg-zinc-900">
                            <td className="px-4 py-3 font-semibold text-slate-900 dark:text-slate-100">{item.test_name}</td>
                            <td className="px-4 py-3">{item.correct_answers}/{item.total_questions}</td>
                            <td className="px-4 py-3">{formatNumber(item.percentage)}%</td>
                            <td className="px-4 py-3">{formatTime(item.time_taken_seconds)}</td>
                            <td className="px-4 py-3">{formatDate(item.attempted_at)}</td>
                            <td className="px-4 py-3">
                              <Link href={`/results/${item.id}`} className="rounded-full bg-blue-500 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-600">
                                View Details
                              </Link>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>

                <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3 text-sm text-slate-600 dark:text-slate-400">
                    <span>Page {filters.page} of {pageCount || 1}</span>
                    <span>|</span>
                    <label className="inline-flex items-center gap-2">
                      Show
                      <select
                        value={filters.pageSize}
                        onChange={(e) => setFilters((prev) => ({ ...prev, pageSize: Number(e.target.value), page: 1 }))}
                        className="rounded-full border border-slate-300 bg-white px-3 py-1 text-sm text-slate-900 outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-slate-100"
                      >
                        {PAGE_SIZES.map((size) => (
                          <option key={size} value={size}>{size}</option>
                        ))}
                      </select>
                      rows
                    </label>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={filters.page <= 1}
                      onClick={() => setFilters((prev) => ({ ...prev, page: Math.max(prev.page - 1, 1) }))}
                      className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-slate-100"
                    >
                      Previous
                    </button>
                    <button
                      type="button"
                      disabled={filters.page >= pageCount}
                      onClick={() => setFilters((prev) => ({ ...prev, page: Math.min(prev.page + 1, pageCount) }))}
                      className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-slate-100"
                    >
                      Next
                    </button>
                  </div>
                </div>
              </div>
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}
