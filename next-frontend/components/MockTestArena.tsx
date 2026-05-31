"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Award,
  BarChart3,
  BookOpen,
  BrainCircuit,
  CheckCircle2,
  Code2,
  Flame,
  Gauge,
  GraduationCap,
  Loader2,
  Moon,
  Network,
  Play,
  Sparkles,
  Sun,
  Timer,
  Trophy,
  XCircle,
} from "lucide-react";
import { API_BASE } from "../lib/api";

type TestType = "dsa" | "aptitude" | "verbal" | "logical" | "programming";

interface TestCard {
  id: TestType;
  title: string;
  description: string;
  accent: string;
  icon: React.ElementType;
}

interface Question {
  id: number;
  topic: string;
  difficulty: string;
  question_type: string;
  prompt: string;
  options: string[];
  correct_answer: string;
  explanation: string;
}

interface ActiveAttempt {
  attempt_id: number;
  question_id: number;
  test_type: TestType;
  title: string;
  timer_seconds: number;
  question: Question;
}

interface Evaluation {
  is_correct: boolean;
  xp: number;
  correct_answer: string;
  explanation: string;
  feedback: string;
}

interface AptitudeQuestion {
  id: number;
  number: number;
  topic: string;
  difficulty: string;
  question_type: string;
  prompt: string;
  options: string[];
}

interface AptitudeAttempt {
  attempt_id: number;
  title: string;
  timer_seconds: number;
  questions: AptitudeQuestion[];
}

interface AptitudeResult {
  score: number;
  total: number;
  correct: number;
  wrong: number;
  accuracy: number;
  time_taken_seconds: number;
  topic_performance: Array<{ topic: string; total: number; correct: number }>;
  difficulty_analysis: Array<{ difficulty: string; total: number; correct: number }>;
  weak_areas: Array<{ topic: string; total: number; correct: number }>;
  strong_areas: Array<{ topic: string; total: number; correct: number }>;
  suggestions: string[];
  rank_estimation: string;
  results: Array<{
    id: number;
    number: number;
    topic: string;
    difficulty: string;
    prompt: string;
    options: string[];
    user_answer: string;
    correct_answer: string;
    is_correct: boolean;
    explanation: string;
  }>;
}

interface Analytics {
  answered: number;
  correct: number;
  accuracy: number;
  avg_time: number;
  streak: number;
  xp: number;
  strong_topics: Array<{ topic: string; answered: number; correct: number }>;
  weak_topics: Array<{ topic: string; answered: number; correct: number }>;
  progress: Array<{ day: string; xp: number }>;
  leaderboard: Array<{ user_id: string; xp: number; correct: number }>;
}

const TESTS: TestCard[] = [
  {
    id: "dsa",
    title: "DSA Mock Test",
    description: "Adaptive coding problem from your weak LeetCode/GFG areas.",
    accent: "from-emerald-500 via-teal-500 to-cyan-500",
    icon: Network,
  },
  {
    id: "aptitude",
    title: "Aptitude Mock Test",
    description: "Timed quantitative questions with instant explanations.",
    accent: "from-amber-500 via-orange-500 to-rose-500",
    icon: Gauge,
  },
  {
    id: "verbal",
    title: "Verbal Ability Mock Test",
    description: "Grammar, vocabulary, comprehension, and sentence logic.",
    accent: "from-sky-500 via-blue-500 to-indigo-500",
    icon: BookOpen,
  },
  {
    id: "logical",
    title: "Logical Reasoning Mock Test",
    description: "Fresh reasoning puzzles that adapt to weak patterns.",
    accent: "from-fuchsia-500 via-pink-500 to-rose-500",
    icon: BrainCircuit,
  },
  {
    id: "programming",
    title: "Programming Concepts Mock Test",
    description: "Language-specific MCQs, snippets, debugging, and concepts.",
    accent: "from-violet-500 via-purple-500 to-blue-500",
    icon: Code2,
  },
];

const LANGUAGES = ["Python", "JavaScript", "Java", "C++", "C", "Go", "Rust"];

function getUserId() {
  if (typeof window === "undefined") return "default_user";
  const existing = window.localStorage.getItem("mock_arena_user_id");
  if (existing) return existing;
  const created = `arena-${crypto.randomUUID()}`;
  window.localStorage.setItem("mock_arena_user_id", created);
  return created;
}

function formatTime(seconds: number) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export default function MockTestArena() {
  const [selectedTest, setSelectedTest] = useState<TestType>("dsa");
  const [leetcodeUsername, setLeetcodeUsername] = useState("");
  const [gfgUsername, setGfgUsername] = useState("");
  const [language, setLanguage] = useState("Python");
  const [activeAttempt, setActiveAttempt] = useState<ActiveAttempt | null>(null);
  const [answer, setAnswer] = useState("");
  const [timeLeft, setTimeLeft] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [darkMode, setDarkMode] = useState(true);
  const [aptitudeAttempt, setAptitudeAttempt] = useState<AptitudeAttempt | null>(null);
  const [aptitudeAnswers, setAptitudeAnswers] = useState<Record<string, string>>({});
  const [aptitudeIndex, setAptitudeIndex] = useState(0);
  const [aptitudeResult, setAptitudeResult] = useState<AptitudeResult | null>(null);
  const [aptitudeElapsed, setAptitudeElapsed] = useState(0);
  const [aptitudeTimeLeft, setAptitudeTimeLeft] = useState(0);
  const [submittingAptitude, setSubmittingAptitude] = useState(false);

  const userId = useMemo(getUserId, []);
  const selectedMeta = TESTS.find((test) => test.id === selectedTest) ?? TESTS[0];

  useEffect(() => {
    async function loadAnalytics() {
      try {
        const res = await fetch(`${API_BASE}/mock-tests/analytics/${userId}`);
        if (!res.ok) return;
        setAnalytics(await res.json());
      } catch (err) {
        console.error(err);
      }
    }

    loadAnalytics();
  }, [userId]);

  useEffect(() => {
    if (!activeAttempt || evaluation) return;
    setTimeLeft(activeAttempt.timer_seconds);
    setElapsed(0);
  }, [activeAttempt, evaluation]);

  useEffect(() => {
    if (!activeAttempt || evaluation || timeLeft <= 0) return;
    const timer = window.setInterval(() => {
      setTimeLeft((prev) => Math.max(0, prev - 1));
      setElapsed((prev) => prev + 1);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [activeAttempt, evaluation, timeLeft]);

  useEffect(() => {
    if (!aptitudeAttempt || aptitudeResult) return;
    setAptitudeTimeLeft(aptitudeAttempt.timer_seconds);
    setAptitudeElapsed(0);
  }, [aptitudeAttempt, aptitudeResult]);

  useEffect(() => {
    if (!aptitudeAttempt || aptitudeResult || aptitudeTimeLeft <= 0) return;
    const timer = window.setInterval(() => {
      setAptitudeTimeLeft((prev) => Math.max(0, prev - 1));
      setAptitudeElapsed((prev) => prev + 1);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [aptitudeAttempt, aptitudeResult, aptitudeTimeLeft]);

  useEffect(() => {
    if (!aptitudeAttempt) return;
    window.localStorage.setItem(
      `aptitude_answers_${aptitudeAttempt.attempt_id}`,
      JSON.stringify(aptitudeAnswers)
    );
  }, [aptitudeAnswers, aptitudeAttempt]);

  async function refreshAnalytics() {
    const res = await fetch(`${API_BASE}/mock-tests/analytics/${userId}`);
    if (res.ok) setAnalytics(await res.json());
  }

  async function startTest(testType = selectedTest) {
    if (testType === "aptitude") {
      await generateAptitudeTest();
      return;
    }

    setSelectedTest(testType);
    setLoading(true);
    setError(null);
    setEvaluation(null);
    setAnswer("");

    try {
      const res = await fetch(`${API_BASE}/mock-tests/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          test_type: testType,
          leetcode_username: leetcodeUsername,
          gfg_username: gfgUsername,
          language,
        }),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail ?? "Could not start mock test");
      }

      setActiveAttempt(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start mock test");
    } finally {
      setLoading(false);
    }
  }

  async function generateAptitudeTest() {
    setSelectedTest("aptitude");
    setLoading(true);
    setError(null);
    setAptitudeResult(null);
    setAptitudeAnswers({});
    setAptitudeIndex(0);
    setActiveAttempt(null);
    setEvaluation(null);

    try {
      const res = await fetch(`${API_BASE}/aptitude-tests/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail ?? "Could not generate aptitude test");
      }
      const data = await res.json();
      setAptitudeAttempt(data);
      const saved = window.localStorage.getItem(`aptitude_answers_${data.attempt_id}`);
      setAptitudeAnswers(saved ? JSON.parse(saved) : {});
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate aptitude test");
    } finally {
      setLoading(false);
    }
  }

  async function submitAptitudeTest() {
    if (!aptitudeAttempt) return;
    setSubmittingAptitude(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/aptitude-tests/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          attempt_id: aptitudeAttempt.attempt_id,
          answers: aptitudeAnswers,
          time_spent_seconds: aptitudeElapsed,
        }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail ?? "Could not submit aptitude test");
      }
      setAptitudeResult(await res.json());
      window.localStorage.removeItem(`aptitude_answers_${aptitudeAttempt.attempt_id}`);
      await refreshAnalytics();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit aptitude test");
    } finally {
      setSubmittingAptitude(false);
    }
  }

  async function submitAnswer() {
    if (!activeAttempt || !answer.trim()) return;
    setSubmitting(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/mock-tests/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question_id: activeAttempt.question.id,
          answer,
          time_spent_seconds: elapsed,
        }),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail ?? "Could not submit answer");
      }

      setEvaluation(await res.json());
      await refreshAnalytics();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit answer");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className={darkMode ? "dark" : ""}>
      <div className="min-h-screen bg-slate-50 text-slate-950 transition-colors dark:bg-zinc-950 dark:text-zinc-50">
        <header className="border-b border-slate-200 bg-white/80 px-4 py-4 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80 md:px-8">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
            <div>
              <Link href="/" className="text-xs font-medium text-blue-600 dark:text-blue-400">
                Back to Chat
              </Link>
              <h1 className="mt-1 text-2xl font-semibold tracking-normal md:text-3xl">
                Mock Test Arena
              </h1>
            </div>
            <button
              type="button"
              onClick={() => setDarkMode((value) => !value)}
              className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-300 bg-white text-slate-700 transition hover:bg-slate-100 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
              title="Toggle theme"
            >
              {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
          </div>
        </header>

        <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 md:px-8 lg:grid-cols-[1fr_360px]">
          <section className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {TESTS.map((test) => {
                const Icon = test.icon;
                const isSelected = selectedTest === test.id;
                return (
                  <button
                    key={test.id}
                    type="button"
                    onClick={() => setSelectedTest(test.id)}
                    className={`group overflow-hidden rounded-2xl border text-left shadow-sm transition duration-300 hover:-translate-y-1 hover:shadow-xl ${
                      isSelected
                        ? "border-blue-500 bg-white dark:border-blue-400 dark:bg-zinc-900"
                        : "border-slate-200 bg-white dark:border-zinc-800 dark:bg-zinc-900"
                    }`}
                  >
                    <div className={`h-2 bg-gradient-to-r ${test.accent}`} />
                    <div className="p-5">
                      <div className={`mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${test.accent} text-white shadow-lg`}>
                        <Icon className="h-6 w-6" />
                      </div>
                      <h2 className="text-lg font-semibold">{test.title}</h2>
                      <p className="mt-2 min-h-12 text-sm leading-6 text-slate-600 dark:text-zinc-400">
                        {test.description}
                      </p>
                      <div className="mt-5 flex items-center justify-between">
                        <span className="text-xs font-medium text-slate-500 dark:text-zinc-500">
                          Adaptive AI
                        </span>
                        <span className="inline-flex items-center gap-2 rounded-full bg-slate-950 px-3 py-2 text-xs font-medium text-white transition group-hover:bg-blue-600 dark:bg-zinc-100 dark:text-zinc-950">
                          <Play className="h-3.5 w-3.5" />
                          Start Test
                        </span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase text-blue-600 dark:text-blue-400">
                    Selected Arena
                  </p>
                  <h2 className="mt-1 text-xl font-semibold">{selectedMeta.title}</h2>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-zinc-400">
                    Questions are generated uniquely per attempt and avoid recently asked prompts where possible.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => startTest(selectedTest)}
                  disabled={loading}
                  className={`inline-flex h-11 items-center gap-2 rounded-full bg-gradient-to-r ${selectedMeta.accent} px-5 text-sm font-semibold text-white shadow-lg transition hover:scale-[1.02] disabled:opacity-60`}
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  Generate Test
                </button>
              </div>

              {selectedTest === "dsa" || selectedTest === "programming" ? (
                <div className={`mt-5 grid gap-4 ${selectedTest === "dsa" ? "md:grid-cols-2" : "md:grid-cols-3"}`}>
                  {selectedTest === "dsa" ? (
                    <>
                      <label className="text-sm">
                        <span className="mb-2 block font-medium">LeetCode username</span>
                        <input
                          value={leetcodeUsername}
                          onChange={(e) => setLeetcodeUsername(e.target.value)}
                          placeholder="optional"
                          className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 outline-none focus:border-blue-500 dark:border-zinc-700 dark:bg-zinc-950"
                        />
                      </label>
                      <label className="text-sm">
                        <span className="mb-2 block font-medium">GeeksforGeeks username</span>
                        <input
                          value={gfgUsername}
                          onChange={(e) => setGfgUsername(e.target.value)}
                          placeholder="optional"
                          className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 outline-none focus:border-blue-500 dark:border-zinc-700 dark:bg-zinc-950"
                        />
                      </label>
                    </>
                  ) : null}

                  {selectedTest === "programming" ? (
                    <label className="text-sm md:col-span-1">
                      <span className="mb-2 block font-medium">Programming language</span>
                      <select
                        value={language}
                        onChange={(e) => setLanguage(e.target.value)}
                        className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 outline-none focus:border-blue-500 dark:border-zinc-700 dark:bg-zinc-950"
                      >
                        {LANGUAGES.map((item) => (
                          <option key={item}>{item}</option>
                        ))}
                      </select>
                    </label>
                  ) : null}
                </div>
              ) : null}

              {error ? (
                <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-300">
                  {error}
                </div>
              ) : null}
            </div>

            {aptitudeAttempt && !aptitudeResult ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase text-slate-500 dark:text-zinc-500">
                      Full Aptitude Mock Test
                    </p>
                    <h2 className="mt-1 text-xl font-semibold">
                      Question {aptitudeIndex + 1} of {aptitudeAttempt.questions.length}
                    </h2>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-sm font-medium dark:bg-zinc-800">
                      <Timer className="h-4 w-4" />
                      {formatTime(aptitudeTimeLeft)}
                    </span>
                    <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                      {Object.keys(aptitudeAnswers).length}/{aptitudeAttempt.questions.length} answered
                    </span>
                  </div>
                </div>

                <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-zinc-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-amber-500 to-rose-500 transition-all"
                    style={{
                      width: `${(Object.keys(aptitudeAnswers).length / aptitudeAttempt.questions.length) * 100}%`,
                    }}
                  />
                </div>

                <div className="mt-5 flex flex-wrap gap-2">
                  {aptitudeAttempt.questions.map((question, index) => (
                    <button
                      key={question.id}
                      type="button"
                      onClick={() => setAptitudeIndex(index)}
                      className={`h-9 w-9 rounded-full text-sm font-semibold transition ${
                        aptitudeIndex === index
                          ? "bg-blue-600 text-white"
                          : aptitudeAnswers[String(question.id)]
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                            : "bg-slate-100 text-slate-600 dark:bg-zinc-800 dark:text-zinc-300"
                      }`}
                    >
                      {index + 1}
                    </button>
                  ))}
                </div>

                {(() => {
                  const question = aptitudeAttempt.questions[aptitudeIndex];
                  return (
                    <div className="mt-6 rounded-2xl border border-slate-200 p-5 dark:border-zinc-800">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-950/50 dark:text-blue-300">
                          {question.topic}
                        </span>
                        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700 dark:bg-zinc-800 dark:text-zinc-300">
                          {question.difficulty}
                        </span>
                      </div>
                      <p className="mt-4 text-base font-medium leading-7">
                        {question.prompt}
                      </p>
                      <div className="mt-5 grid gap-3 md:grid-cols-2">
                        {question.options.map((option) => {
                          const value = option.slice(0, 1);
                          const checked = aptitudeAnswers[String(question.id)] === value;
                          return (
                            <label
                              key={option}
                              className={`flex cursor-pointer items-center gap-3 rounded-2xl border px-4 py-3 text-sm transition ${
                                checked
                                  ? "border-blue-500 bg-blue-50 dark:bg-blue-950/40"
                                  : "border-slate-200 hover:bg-slate-50 dark:border-zinc-800 dark:hover:bg-zinc-800"
                              }`}
                            >
                              <input
                                type="radio"
                                name={`aptitude-${question.id}`}
                                checked={checked}
                                onChange={() =>
                                  setAptitudeAnswers((prev) => ({
                                    ...prev,
                                    [String(question.id)]: value,
                                  }))
                                }
                              />
                              <span>{option}</span>
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  );
                })()}

                <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setAptitudeIndex((prev) => Math.max(0, prev - 1))}
                      disabled={aptitudeIndex === 0}
                      className="rounded-full border border-slate-300 px-4 py-2 text-sm font-medium disabled:opacity-50 dark:border-zinc-700"
                    >
                      Previous
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        setAptitudeIndex((prev) =>
                          Math.min(aptitudeAttempt.questions.length - 1, prev + 1)
                        )
                      }
                      disabled={aptitudeIndex === aptitudeAttempt.questions.length - 1}
                      className="rounded-full border border-slate-300 px-4 py-2 text-sm font-medium disabled:opacity-50 dark:border-zinc-700"
                    >
                      Next
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={submitAptitudeTest}
                    disabled={submittingAptitude}
                    className="inline-flex h-10 items-center gap-2 rounded-full bg-slate-950 px-5 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-950"
                  >
                    {submittingAptitude ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                    Submit Test
                  </button>
                </div>
              </div>
            ) : null}

            {aptitudeResult ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase text-emerald-600 dark:text-emerald-400">
                      Aptitude Result
                    </p>
                    <h2 className="mt-1 text-2xl font-semibold">
                      {aptitudeResult.score}/{aptitudeResult.total} Score
                    </h2>
                    <p className="mt-2 text-sm text-slate-600 dark:text-zinc-400">
                      Rank estimation: {aptitudeResult.rank_estimation}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={generateAptitudeTest}
                    className="rounded-full bg-blue-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-blue-700"
                  >
                    Retake Fresh Test
                  </button>
                </div>

                <div className="mt-5 grid gap-3 md:grid-cols-4">
                  <Metric icon={Award} label="Accuracy" value={`${aptitudeResult.accuracy}%`} />
                  <Metric icon={CheckCircle2} label="Correct" value={`${aptitudeResult.correct}`} />
                  <Metric icon={XCircle} label="Wrong" value={`${aptitudeResult.wrong}`} />
                  <Metric icon={Timer} label="Time" value={formatTime(aptitudeResult.time_taken_seconds)} />
                </div>

                <div className="mt-6 grid gap-4 md:grid-cols-2">
                  <ResultPanel title="Strong Areas" items={aptitudeResult.strong_areas} />
                  <ResultPanel title="Weak Areas" items={aptitudeResult.weak_areas} />
                </div>

                <div className="mt-6 rounded-2xl bg-slate-50 p-4 dark:bg-zinc-950">
                  <h3 className="font-semibold">Improvement Suggestions</h3>
                  <ul className="mt-3 space-y-2 text-sm text-slate-700 dark:text-zinc-300">
                    {aptitudeResult.suggestions.map((item) => (
                      <li key={item}>- {item}</li>
                    ))}
                  </ul>
                </div>

                <div className="mt-6 space-y-3">
                  <h3 className="font-semibold">Answer Review</h3>
                  {aptitudeResult.results.map((item) => (
                    <div
                      key={item.id}
                      className="rounded-2xl border border-slate-200 p-4 dark:border-zinc-800"
                    >
                      <div className="flex flex-wrap items-center gap-2 text-xs font-semibold">
                        <span>Q{item.number}</span>
                        <span className="rounded-full bg-slate-100 px-2 py-1 dark:bg-zinc-800">{item.topic}</span>
                        <span className={item.is_correct ? "text-emerald-500" : "text-rose-500"}>
                          {item.is_correct ? "Correct" : "Wrong"}
                        </span>
                      </div>
                      <p className="mt-3 text-sm font-medium">{item.prompt}</p>
                      <p className="mt-2 text-sm text-slate-600 dark:text-zinc-400">
                        Your answer: {item.user_answer || "Not answered"} | Correct answer: {item.correct_answer}
                      </p>
                      <p className="mt-2 text-sm text-slate-700 dark:text-zinc-300">
                        {item.explanation}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {activeAttempt ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase text-slate-500 dark:text-zinc-500">
                      {activeAttempt.title}
                    </p>
                    <h2 className="mt-1 text-xl font-semibold">
                      {activeAttempt.question.topic}
                    </h2>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-950/50 dark:text-blue-300">
                      {activeAttempt.question.difficulty}
                    </span>
                    <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-sm font-medium dark:bg-zinc-800">
                      <Timer className="h-4 w-4" />
                      {formatTime(timeLeft)}
                    </span>
                  </div>
                </div>

                <pre className="mt-5 whitespace-pre-wrap rounded-2xl bg-slate-950 p-5 text-sm leading-6 text-slate-50 dark:bg-black">
                  {activeAttempt.question.prompt}
                </pre>

                {activeAttempt.question.options.length > 0 ? (
                  <div className="mt-4 grid gap-2 sm:grid-cols-2">
                    {activeAttempt.question.options.map((option) => (
                      <button
                        key={option}
                        type="button"
                        onClick={() => setAnswer(option.slice(0, 1))}
                        className={`rounded-xl border px-4 py-3 text-left text-sm transition ${
                          answer === option.slice(0, 1)
                            ? "border-blue-500 bg-blue-50 dark:bg-blue-950/40"
                            : "border-slate-200 hover:bg-slate-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
                        }`}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                ) : (
                  <textarea
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    rows={7}
                    placeholder="Write your approach, answer, complexity, edge cases, or explanation..."
                    className="mt-4 w-full resize-none rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-blue-500 dark:border-zinc-700 dark:bg-zinc-950"
                  />
                )}

                <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                  <button
                    type="button"
                    onClick={submitAnswer}
                    disabled={submitting || !answer.trim() || !!evaluation}
                    className="inline-flex h-10 items-center gap-2 rounded-full bg-slate-950 px-5 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-950"
                  >
                    {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                    Submit Answer
                  </button>
                  <button
                    type="button"
                    onClick={() => startTest(activeAttempt.test_type)}
                    className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400"
                  >
                    Generate another unique question
                  </button>
                </div>

                {evaluation ? (
                  <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-5 dark:border-zinc-800 dark:bg-zinc-950">
                    <div className="flex items-center gap-3">
                      {evaluation.is_correct ? (
                        <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                      ) : (
                        <XCircle className="h-5 w-5 text-rose-500" />
                      )}
                      <h3 className="font-semibold">
                        {evaluation.is_correct ? "Correct" : "Needs Improvement"} - +{evaluation.xp} XP
                      </h3>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-slate-700 dark:text-zinc-300">
                      {evaluation.feedback}
                    </p>
                    <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-zinc-400">
                      <strong>Explanation:</strong> {evaluation.explanation}
                    </p>
                  </div>
                ) : null}
              </div>
            ) : null}
          </section>

          <aside className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <h2 className="flex items-center gap-2 font-semibold">
                <BarChart3 className="h-5 w-5 text-blue-500" />
                Performance Analytics
              </h2>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <Metric icon={Award} label="Accuracy" value={`${analytics?.accuracy ?? 0}%`} />
                <Metric icon={Timer} label="Avg Speed" value={`${analytics?.avg_time ?? 0}s`} />
                <Metric icon={Flame} label="Streak" value={`${analytics?.streak ?? 0}d`} />
                <Metric icon={Sparkles} label="XP" value={`${analytics?.xp ?? 0}`} />
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <h2 className="flex items-center gap-2 font-semibold">
                <GraduationCap className="h-5 w-5 text-emerald-500" />
                Topic Signals
              </h2>
              <TopicList title="Strong" topics={analytics?.strong_topics ?? []} />
              <TopicList title="Weak" topics={analytics?.weak_topics ?? []} />
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <h2 className="flex items-center gap-2 font-semibold">
                <Trophy className="h-5 w-5 text-amber-500" />
                Leaderboard
              </h2>
              <div className="mt-4 space-y-2">
                {(analytics?.leaderboard ?? []).length === 0 ? (
                  <p className="text-sm text-slate-500 dark:text-zinc-400">No attempts yet.</p>
                ) : (
                  analytics?.leaderboard.map((row, index) => (
                    <div
                      key={row.user_id}
                      className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-sm dark:bg-zinc-950"
                    >
                      <span className="truncate">#{index + 1} {row.user_id}</span>
                      <span className="font-semibold">{row.xp} XP</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl bg-slate-50 p-3 dark:bg-zinc-950">
      <Icon className="h-4 w-4 text-blue-500" />
      <p className="mt-2 text-xs text-slate-500 dark:text-zinc-500">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}

function TopicList({
  title,
  topics,
}: {
  title: string;
  topics: Array<{ topic: string; answered: number; correct: number }>;
}) {
  return (
    <div className="mt-4">
      <p className="text-xs font-semibold uppercase text-slate-500 dark:text-zinc-500">
        {title}
      </p>
      <div className="mt-2 space-y-2">
        {topics.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-zinc-400">Not enough data yet.</p>
        ) : (
          topics.map((topic) => (
            <div key={topic.topic} className="rounded-xl bg-slate-50 px-3 py-2 dark:bg-zinc-950">
              <div className="flex justify-between gap-3 text-sm">
                <span className="truncate">{topic.topic}</span>
                <span>{topic.correct}/{topic.answered}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function ResultPanel({
  title,
  items,
}: {
  title: string;
  items: Array<{ topic: string; total: number; correct: number }>;
}) {
  return (
    <div className="rounded-2xl bg-slate-50 p-4 dark:bg-zinc-950">
      <h3 className="font-semibold">{title}</h3>
      <div className="mt-3 space-y-2">
        {items.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-zinc-400">No data yet.</p>
        ) : (
          items.map((item) => (
            <div key={item.topic} className="flex items-center justify-between gap-3 text-sm">
              <span className="truncate">{item.topic}</span>
              <span className="font-medium">
                {item.correct}/{item.total}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
