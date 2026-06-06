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
import { API_BASE, authFetch } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

type Arena = "dsa" | "aptitude" | "verbal" | "reasoning" | "programming";
type McqArena = Exclude<Arena, "dsa">;

interface TestCard {
  id: Arena;
  title: string;
  description: string;
  accent: string;
  icon: React.ElementType;
}

interface MockQuestion {
  id: number;
  number: number;
  topic: string;
  difficulty: string;
  question_type: string;
  prompt: string;
  options: string[];
  correct_answer: string;
  explanation: string;
}

interface TwentyQuestionTest {
  arena: McqArena;
  title: string;
  timer_seconds: number;
  questions: MockQuestion[];
}

interface DsaTest {
  arena: "dsa";
  title: string;
  timer_seconds: number;
  question: MockQuestion;
  profile_context?: {
    total_solved?: number;
    topics?: Array<{ topic_name?: string; name?: string; solved_count?: number }>;
    contests?: unknown[];
  };
}

type ArenaTest = TwentyQuestionTest | DsaTest;

interface TestResult {
  score: number;
  total: number;
  correct: number;
  wrong: number;
  accuracy: number;
  elapsedSeconds: number;
  weakAreas: Array<{ topic: string; total: number; correct: number }>;
  strongAreas: Array<{ topic: string; total: number; correct: number }>;
}

interface DsaEvaluation {
  score: number;
  feedback: string;
  covered: string[];
  missing: string[];
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
  leaderboard: Array<{ user_id: string; xp: number; correct: number }>;
}

const TESTS: TestCard[] = [
  {
    id: "dsa",
    title: "DSA Mock Test",
    description: "One personalized coding problem from weak LeetCode/GFG areas.",
    accent: "from-emerald-500 via-teal-500 to-cyan-500",
    icon: Network,
  },
  {
    id: "aptitude",
    title: "Aptitude Mock Test",
    description: "20 quantitative MCQs with timer and explanations.",
    accent: "from-amber-500 via-orange-500 to-rose-500",
    icon: Gauge,
  },
  {
    id: "verbal",
    title: "Verbal Ability Mock Test",
    description: "20 grammar, vocabulary, and comprehension MCQs.",
    accent: "from-sky-500 via-blue-500 to-indigo-500",
    icon: BookOpen,
  },
  {
    id: "reasoning",
    title: "Logical Reasoning Mock Test",
    description: "20 reasoning puzzles across common interview patterns.",
    accent: "from-fuchsia-500 via-pink-500 to-rose-500",
    icon: BrainCircuit,
  },
  {
    id: "programming",
    title: "Programming Concepts Mock Test",
    description: "20 language-specific concept, debugging, and tracing questions.",
    accent: "from-violet-500 via-purple-500 to-blue-500",
    icon: Code2,
  },
];

const LANGUAGES = ["Python", "JavaScript", "Java", "C++", "C", "Go", "Rust"];
const ARENA_ORDER: Arena[] = ["dsa", "aptitude", "verbal", "reasoning", "programming"];

function emptyArenaMap<T>(value: T): Record<Arena, T> {
  return {
    dsa: value,
    aptitude: value,
    verbal: value,
    reasoning: value,
    programming: value,
  };
}

function formatTime(seconds: number) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function scoreTwentyQuestionTest(
  test: TwentyQuestionTest,
  answers: Record<string, string>,
  elapsedSeconds: number
): TestResult {
  const topicStats: Record<string, { topic: string; total: number; correct: number }> = {};
  let correct = 0;

  for (const question of test.questions) {
    const userAnswer = answers[String(question.id)] ?? "";
    const isCorrect = userAnswer.toUpperCase() === question.correct_answer.toUpperCase();
    if (isCorrect) correct += 1;
    topicStats[question.topic] ??= { topic: question.topic, total: 0, correct: 0 };
    topicStats[question.topic].total += 1;
    if (isCorrect) topicStats[question.topic].correct += 1;
  }

  const total = test.questions.length;
  const topicList = Object.values(topicStats);
  const byAccuracy = (item: { total: number; correct: number }) => item.correct / Math.max(1, item.total);

  return {
    score: correct,
    total,
    correct,
    wrong: total - correct,
    accuracy: total ? Math.round((correct / total) * 1000) / 10 : 0,
    elapsedSeconds,
    weakAreas: [...topicList].sort((a, b) => byAccuracy(a) - byAccuracy(b)).slice(0, 3),
    strongAreas: [...topicList].sort((a, b) => byAccuracy(b) - byAccuracy(a)).slice(0, 3),
  };
}

function evaluateDsaAnswer(answer: string): DsaEvaluation {
  const normalized = answer.toLowerCase();
  const rubric = [
    "constraints",
    "edge cases",
    "algorithm",
    "complexity",
    "data structure",
    "example",
  ];
  const covered = rubric.filter((item) => normalized.includes(item));
  const missing = rubric.filter((item) => !normalized.includes(item));
  const wordScore = Math.min(35, Math.floor(answer.trim().split(/\s+/).length / 3));
  const score = Math.min(100, 25 + covered.length * 8 + wordScore);

  return {
    score,
    covered,
    missing,
    feedback:
      score >= 75
        ? "Strong coding-interview answer. Your response has enough structure and depth to evaluate well."
        : "Good start. Add constraints, edge cases, complexity, and a clearer algorithm walkthrough.",
  };
}

export default function MockTestArena() {
  const [selectedArena, setSelectedArena] = useState<Arena>("dsa");
  const [arenaTests, setArenaTests] = useState<Record<Arena, ArenaTest | null>>(
    emptyArenaMap<ArenaTest | null>(null)
  );
  const [answers, setAnswers] = useState<Record<Arena, Record<string, string>>>(
    emptyArenaMap<Record<string, string>>({})
  );
  const [activeIndex, setActiveIndex] = useState<Record<Arena, number>>(
    emptyArenaMap(0)
  );
  const [results, setResults] = useState<Record<Arena, TestResult | DsaEvaluation | null>>(
    emptyArenaMap<TestResult | DsaEvaluation | null>(null)
  );
  const [timeLeft, setTimeLeft] = useState<Record<Arena, number>>(emptyArenaMap(0));
  const [elapsed, setElapsed] = useState<Record<Arena, number>>(emptyArenaMap(0));
  const [leetcodeUsername, setLeetcodeUsername] = useState("");
  const [gfgUsername, setGfgUsername] = useState("");
  const [language, setLanguage] = useState("Python");
  const [loadingArena, setLoadingArena] = useState<Arena | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [darkMode, setDarkMode] = useState(true);

  const { token } = useAuth();
  const selectedMeta = TESTS.find((test) => test.id === selectedArena) ?? TESTS[0];
  const selectedTest = arenaTests[selectedArena];
  const selectedResult = results[selectedArena];

  useEffect(() => {
    async function loadAnalytics() {
      try {
        if (!token) return;
        const data = await authFetch<Analytics>(`${API_BASE}/mock-tests/analytics`, token);
        setAnalytics(data);
      } catch (err) {
        console.error(err);
      }
    }

    loadAnalytics();
  }, [token]);

  useEffect(() => {
    if (!selectedTest || selectedResult || timeLeft[selectedArena] <= 0) return;
    const timer = window.setInterval(() => {
      setTimeLeft((prev) => ({
        ...prev,
        [selectedArena]: Math.max(0, prev[selectedArena] - 1),
      }));
      setElapsed((prev) => ({ ...prev, [selectedArena]: prev[selectedArena] + 1 }));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [selectedArena, selectedTest, selectedResult, timeLeft]);

  async function generateArenaTest(arena: Arena = selectedArena) {
    setSelectedArena(arena);
    setLoadingArena(arena);
    setError(null);

    try {
      if (!token) {
        throw new Error("Session expired. Please sign in again.");
      }

      const data = await authFetch<ArenaTest>(`${API_BASE}/mock/${arena}/generate`, token, {
        method: "POST",
        body: JSON.stringify({
          leetcode_username: leetcodeUsername,
          gfg_username: gfgUsername,
          language,
        }),
      });
      if (data.arena !== arena) {
        throw new Error("Generated test did not match the selected arena");
      }

      setArenaTests((prev) => ({ ...prev, [arena]: data }));
      setAnswers((prev) => ({ ...prev, [arena]: {} }));
      setActiveIndex((prev) => ({ ...prev, [arena]: 0 }));
      setResults((prev) => ({ ...prev, [arena]: null }));
      setTimeLeft((prev) => ({ ...prev, [arena]: data.timer_seconds }));
      setElapsed((prev) => ({ ...prev, [arena]: 0 }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate test");
    } finally {
      setLoadingArena(null);
    }
  }

  function submitTwentyQuestionTest(test: TwentyQuestionTest) {
    const result = scoreTwentyQuestionTest(test, answers[test.arena], elapsed[test.arena]);
    setResults((prev) => ({ ...prev, [test.arena]: result }));
  }

  function submitDsaAnswer(test: DsaTest) {
    const answer = answers.dsa[String(test.question.id)] ?? "";
    if (!answer.trim()) return;
    setResults((prev) => ({ ...prev, dsa: evaluateDsaAnswer(answer) }));
  }

  function selectArena(arena: Arena) {
    setSelectedArena(arena);
    setError(null);
  }

  function renderSelectedArena() {
    if (!selectedTest) return null;
    if (selectedTest.arena !== selectedArena) return null;

    if (selectedTest.arena === "dsa") {
      return (
        <DSAMockTest
          selectedArena={selectedArena}
          test={selectedTest}
          answer={answers.dsa[String(selectedTest.question.id)] ?? ""}
          onAnswer={(value) =>
            setAnswers((prev) => ({
              ...prev,
              dsa: { ...prev.dsa, [String(selectedTest.question.id)]: value },
            }))
          }
          timeLeft={timeLeft.dsa}
          result={results.dsa as DsaEvaluation | null}
          onSubmit={() => submitDsaAnswer(selectedTest)}
          onRegenerate={() => generateArenaTest("dsa")}
        />
      );
    }

    return (
      <TwentyQuestionMockTest
        selectedArena={selectedArena}
        test={selectedTest}
        answers={answers[selectedTest.arena]}
        activeIndex={activeIndex[selectedTest.arena]}
        timeLeft={timeLeft[selectedTest.arena]}
        result={results[selectedTest.arena] as TestResult | null}
        onAnswer={(questionId, value) =>
          setAnswers((prev) => ({
            ...prev,
            [selectedTest.arena]: {
              ...prev[selectedTest.arena],
              [String(questionId)]: value,
            },
          }))
        }
        onIndexChange={(index) =>
          setActiveIndex((prev) => ({ ...prev, [selectedTest.arena]: index }))
        }
        onSubmit={() => submitTwentyQuestionTest(selectedTest)}
        onRegenerate={() => generateArenaTest(selectedTest.arena)}
      />
    );
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
                const isSelected = selectedArena === test.id;
                return (
                  <button
                    key={test.id}
                    type="button"
                    onClick={() => selectArena(test.id)}
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
                          {test.id === "dsa" ? "1 coding problem" : "20 MCQs"}
                        </span>
                        <span className="inline-flex items-center gap-2 rounded-full bg-slate-950 px-3 py-2 text-xs font-medium text-white transition group-hover:bg-blue-600 dark:bg-zinc-100 dark:text-zinc-950">
                          <Play className="h-3.5 w-3.5" />
                          Select
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
                    Each arena has isolated state. Switching arenas hides previous test content completely.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => generateArenaTest(selectedArena)}
                  disabled={loadingArena === selectedArena}
                  className={`inline-flex h-11 items-center gap-2 rounded-full bg-gradient-to-r ${selectedMeta.accent} px-5 text-sm font-semibold text-white shadow-lg transition hover:scale-[1.02] disabled:opacity-60`}
                >
                  {loadingArena === selectedArena ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4" />
                  )}
                  Generate Test
                </button>
              </div>

              {selectedArena === "dsa" || selectedArena === "programming" ? (
                <div className={`mt-5 grid gap-4 ${selectedArena === "dsa" ? "md:grid-cols-2" : "md:grid-cols-3"}`}>
                  {selectedArena === "dsa" ? (
                    <>
                      <InputField label="LeetCode username" value={leetcodeUsername} onChange={setLeetcodeUsername} />
                      <InputField label="GeeksforGeeks username" value={gfgUsername} onChange={setGfgUsername} />
                    </>
                  ) : null}

                  {selectedArena === "programming" ? (
                    <label className="text-sm md:col-span-1">
                      <span className="mb-2 block font-medium">Programming language</span>
                      <select
                        value={language}
                        onChange={(event) => setLanguage(event.target.value)}
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

            {renderSelectedArena()}
          </section>

          <aside className="space-y-4">
            <AnalyticsPanel analytics={analytics} />
            <ArenaStatePanel arenaTests={arenaTests} />
          </aside>
        </div>
      </div>
    </main>
  );
}

function InputField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-sm">
      <span className="mb-2 block font-medium">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="optional"
        className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 outline-none focus:border-blue-500 dark:border-zinc-700 dark:bg-zinc-950"
      />
    </label>
  );
}

function AptitudeMockTest(props: TwentyQuestionProps) {
  return <TwentyQuestionMockTest {...props} />;
}

function VerbalMockTest(props: TwentyQuestionProps) {
  return <TwentyQuestionMockTest {...props} />;
}

function ReasoningMockTest(props: TwentyQuestionProps) {
  return <TwentyQuestionMockTest {...props} />;
}

function ProgrammingConceptMockTest(props: TwentyQuestionProps) {
  return <TwentyQuestionMockTest {...props} />;
}

interface TwentyQuestionProps {
  selectedArena: Arena;
  test: TwentyQuestionTest;
  answers: Record<string, string>;
  activeIndex: number;
  timeLeft: number;
  result: TestResult | null;
  onAnswer: (questionId: number, value: string) => void;
  onIndexChange: (index: number) => void;
  onSubmit: () => void;
  onRegenerate: () => void;
}

function TwentyQuestionMockTest(props: TwentyQuestionProps) {
  const { selectedArena, test } = props;
  if (test.arena !== selectedArena) return null;

  if (test.arena === "aptitude") return <AptitudeTestContent {...props} />;
  if (test.arena === "verbal") return <VerbalTestContent {...props} />;
  if (test.arena === "reasoning") return <ReasoningTestContent {...props} />;
  return <ProgrammingTestContent {...props} />;
}

function AptitudeTestContent(props: TwentyQuestionProps) {
  return <TwentyQuestionContent {...props} />;
}

function VerbalTestContent(props: TwentyQuestionProps) {
  return <TwentyQuestionContent {...props} />;
}

function ReasoningTestContent(props: TwentyQuestionProps) {
  return <TwentyQuestionContent {...props} />;
}

function ProgrammingTestContent(props: TwentyQuestionProps) {
  return <TwentyQuestionContent {...props} />;
}

function TwentyQuestionContent({
  test,
  answers,
  activeIndex,
  timeLeft,
  result,
  onAnswer,
  onIndexChange,
  onSubmit,
  onRegenerate,
}: TwentyQuestionProps) {
  const question = test.questions[activeIndex] ?? test.questions[0];
  const answeredCount = Object.keys(answers).length;

  if (result) {
    return (
      <ResultView
        title={test.title}
        result={result}
        questions={test.questions}
        answers={answers}
        onRegenerate={onRegenerate}
      />
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500 dark:text-zinc-500">
            {test.title}
          </p>
          <h2 className="mt-1 text-xl font-semibold">
            Question {activeIndex + 1} of {test.questions.length}
          </h2>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-sm font-medium dark:bg-zinc-800">
            <Timer className="h-4 w-4" />
            {formatTime(timeLeft)}
          </span>
          <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
            {answeredCount}/{test.questions.length} answered
          </span>
        </div>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-zinc-800">
        <div
          className="h-full rounded-full bg-gradient-to-r from-blue-500 to-emerald-500 transition-all"
          style={{ width: `${(answeredCount / test.questions.length) * 100}%` }}
        />
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {test.questions.map((item, index) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onIndexChange(index)}
            className={`h-9 w-9 rounded-full text-sm font-semibold transition ${
              activeIndex === index
                ? "bg-blue-600 text-white"
                : answers[String(item.id)]
                  ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                  : "bg-slate-100 text-slate-600 dark:bg-zinc-800 dark:text-zinc-300"
            }`}
          >
            {index + 1}
          </button>
        ))}
      </div>

      <div className="mt-6 rounded-2xl border border-slate-200 p-5 dark:border-zinc-800">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-950/50 dark:text-blue-300">
            {question.topic}
          </span>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700 dark:bg-zinc-800 dark:text-zinc-300">
            {question.difficulty}
          </span>
        </div>
        <p className="mt-4 whitespace-pre-wrap text-base font-medium leading-7">
          {question.prompt}
        </p>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          {question.options.map((option) => {
            const value = option.slice(0, 1);
            const checked = answers[String(question.id)] === value;
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
                  name={`${test.arena}-${question.id}`}
                  checked={checked}
                  onChange={() => onAnswer(question.id, value)}
                />
                <span>{option}</span>
              </label>
            );
          })}
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onIndexChange(Math.max(0, activeIndex - 1))}
            disabled={activeIndex === 0}
            className="rounded-full border border-slate-300 px-4 py-2 text-sm font-medium disabled:opacity-50 dark:border-zinc-700"
          >
            Previous
          </button>
          <button
            type="button"
            onClick={() => onIndexChange(Math.min(test.questions.length - 1, activeIndex + 1))}
            disabled={activeIndex === test.questions.length - 1}
            className="rounded-full border border-slate-300 px-4 py-2 text-sm font-medium disabled:opacity-50 dark:border-zinc-700"
          >
            Next
          </button>
        </div>
        <button
          type="button"
          onClick={onSubmit}
          className="inline-flex h-10 items-center gap-2 rounded-full bg-slate-950 px-5 text-sm font-semibold text-white transition hover:bg-blue-600 dark:bg-zinc-100 dark:text-zinc-950"
        >
          <CheckCircle2 className="h-4 w-4" />
          Submit Test
        </button>
      </div>
    </div>
  );
}

function DSAMockTest({
  selectedArena,
  test,
  answer,
  onAnswer,
  timeLeft,
  result,
  onSubmit,
  onRegenerate,
}: {
  selectedArena: Arena;
  test: DsaTest;
  answer: string;
  onAnswer: (value: string) => void;
  timeLeft: number;
  result: DsaEvaluation | null;
  onSubmit: () => void;
  onRegenerate: () => void;
}) {
  if (test.arena !== selectedArena) return null;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500 dark:text-zinc-500">
            {test.title}
          </p>
          <h2 className="mt-1 text-xl font-semibold">{test.question.topic}</h2>
        </div>
        <div className="flex items-center gap-3">
          <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-950/50 dark:text-blue-300">
            {test.question.difficulty}
          </span>
          <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-sm font-medium dark:bg-zinc-800">
            <Timer className="h-4 w-4" />
            {formatTime(timeLeft)}
          </span>
        </div>
      </div>

      <pre className="mt-5 whitespace-pre-wrap rounded-2xl bg-slate-950 p-5 text-sm leading-6 text-slate-50 dark:bg-black">
        {test.question.prompt}
      </pre>

      <textarea
        value={answer}
        onChange={(event) => onAnswer(event.target.value)}
        rows={8}
        placeholder="Write your approach, edge cases, complexity, and implementation plan..."
        className="mt-4 w-full resize-none rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-blue-500 dark:border-zinc-700 dark:bg-zinc-950"
      />

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={onSubmit}
          disabled={!answer.trim()}
          className="inline-flex h-10 items-center gap-2 rounded-full bg-slate-950 px-5 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-950"
        >
          <CheckCircle2 className="h-4 w-4" />
          Submit Answer
        </button>
        <button
          type="button"
          onClick={onRegenerate}
          className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400"
        >
          Generate another DSA problem
        </button>
      </div>

      {result ? (
        <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-5 dark:border-zinc-800 dark:bg-zinc-950">
          <h3 className="font-semibold">Interview Score: {result.score}/100</h3>
          <p className="mt-3 text-sm leading-6 text-slate-700 dark:text-zinc-300">
            {result.feedback}
          </p>
          <p className="mt-3 text-sm text-slate-600 dark:text-zinc-400">
            Expected rubric: {test.question.correct_answer}
          </p>
          <p className="mt-2 text-sm text-slate-600 dark:text-zinc-400">
            Explanation: {test.question.explanation}
          </p>
        </div>
      ) : null}
    </div>
  );
}

function ResultView({
  title,
  result,
  questions,
  answers,
  onRegenerate,
}: {
  title: string;
  result: TestResult;
  questions: MockQuestion[];
  answers: Record<string, string>;
  onRegenerate: () => void;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase text-emerald-600 dark:text-emerald-400">
            {title} Result
          </p>
          <h2 className="mt-1 text-2xl font-semibold">
            {result.score}/{result.total} Score
          </h2>
        </div>
        <button
          type="button"
          onClick={onRegenerate}
          className="rounded-full bg-blue-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-blue-700"
        >
          Retake Fresh Test
        </button>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-4">
        <Metric icon={Award} label="Accuracy" value={`${result.accuracy}%`} />
        <Metric icon={CheckCircle2} label="Correct" value={`${result.correct}`} />
        <Metric icon={XCircle} label="Wrong" value={`${result.wrong}`} />
        <Metric icon={Timer} label="Time" value={formatTime(result.elapsedSeconds)} />
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <ResultPanel title="Strong Areas" items={result.strongAreas} />
        <ResultPanel title="Weak Areas" items={result.weakAreas} />
      </div>

      <div className="mt-6 space-y-3">
        <h3 className="font-semibold">Answer Review</h3>
        {questions.map((item) => {
          const userAnswer = answers[String(item.id)] ?? "";
          const isCorrect = userAnswer === item.correct_answer;
          return (
            <div key={item.id} className="rounded-2xl border border-slate-200 p-4 dark:border-zinc-800">
              <div className="flex flex-wrap items-center gap-2 text-xs font-semibold">
                <span>Q{item.number}</span>
                <span className="rounded-full bg-slate-100 px-2 py-1 dark:bg-zinc-800">
                  {item.topic}
                </span>
                <span className={isCorrect ? "text-emerald-500" : "text-rose-500"}>
                  {isCorrect ? "Correct" : "Wrong"}
                </span>
              </div>
              <p className="mt-3 whitespace-pre-wrap text-sm font-medium">{item.prompt}</p>
              <p className="mt-2 text-sm text-slate-600 dark:text-zinc-400">
                Your answer: {userAnswer || "Not answered"} | Correct answer: {item.correct_answer}
              </p>
              <p className="mt-2 text-sm text-slate-700 dark:text-zinc-300">
                {item.explanation}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AnalyticsPanel({ analytics }: { analytics: Analytics | null }) {
  return (
    <>
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
    </>
  );
}

function ArenaStatePanel({ arenaTests }: { arenaTests: Record<Arena, ArenaTest | null> }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <h2 className="font-semibold">Generated Arenas</h2>
      <div className="mt-4 space-y-2">
        {ARENA_ORDER.map((arena) => (
          <div
            key={arena}
            className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-sm dark:bg-zinc-950"
          >
            <span className="capitalize">{arena === "reasoning" ? "logical reasoning" : arena}</span>
            <span className={arenaTests[arena] ? "text-emerald-500" : "text-slate-400"}>
              {arenaTests[arena] ? "Ready" : "Empty"}
            </span>
          </div>
        ))}
      </div>
    </div>
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
