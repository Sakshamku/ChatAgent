export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api";

export interface SignupPayload {
  full_name: string;
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface AuthResponse<T = unknown> {
  access_token: string;
  token_type: string;
  user: T;
}

const defaultHeaders = {
  "Content-Type": "application/json",
};

export async function authFetch<T = unknown>(
  route: string,
  token?: string | null,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers({
    ...defaultHeaders,
    ...(options.headers || {}),
  });

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(route, {
    ...options,
    headers,
    credentials: "same-origin",
  });

  if (!response.ok) {
    let detail = "Unknown error";
    try {
      const body = await response.json();
      detail = body?.detail || body?.message || detail;
    } catch {
      detail = await response.text();
    }
    throw new Error(detail || response.statusText);
  }

  return response.json();
}

export async function signup(payload: SignupPayload): Promise<AuthResponse> {
  return authFetch(`${API_BASE}/auth/signup`, null, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  return authFetch(`${API_BASE}/auth/login`, null, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getCurrentUser(token: string): Promise<unknown> {
  return authFetch(`${API_BASE}/auth/me`, token);
}

// ==================== MOCK TEST RESULTS APIs ====================

export interface SubjectResult {
  id: string;
  test_result_id: string;
  subject_name: string;
  total_questions: number;
  correct_answers: number;
  wrong_answers: number;
  score: number;
  percentage: number;
}

export interface TestResult {
  id: string;
  user_id: string;
  test_id?: string;
  test_name: string;
  total_questions: number;
  attempted_questions: number;
  correct_answers: number;
  wrong_answers: number;
  unattempted_questions: number;
  score: number;
  accuracy: number;
  percentage: number;
  time_taken_seconds: number;
  attempted_at: string;
  subjects?: SubjectResult[];
}

export interface TestResultCreate {
  test_name: string;
  total_questions: number;
  correct_answers: number;
  wrong_answers: number;
  unattempted_questions: number;
  score: number;
  percentage: number;
  time_taken_seconds: number;
  subjects?: Array<{
    subject_name: string;
    total_questions: number;
    correct_answers: number;
    wrong_answers: number;
    score: number;
    percentage: number;
  }>;
}

export interface TestSubmitPayload {
  test_id?: string;
  test_name: string;
  total_questions: number;
  time_taken_seconds: number;
  questions: Array<{
    question_id: string | number;
    subject: string;
    selected_answer?: string;
    correct_answer?: string;
    time_spent?: number;
  }>;
}

export interface Analytics {
  total_tests: number;
  average_score: number;
  best_score: number;
  worst_score: number;
  average_accuracy: number;
}

export interface SubjectPerformance {
  subject: string;
  average_percentage: number;
  best_percentage: number;
  total_tests: number;
  total_questions: number;
  total_correct: number;
  total_wrong: number;
}

export interface ProgressDataPoint {
  test_name: string;
  score: number;
  attempted_at: string;
  percentage?: number;
}

export interface AccuracyTrendPoint {
  test_name: string;
  accuracy: number;
  attempted_at: string;
}

export interface ProfileOverview {
  total_tests: number;
  average_score: number;
  best_score: number;
  lowest_score: number;
  accuracy: number;
  total_questions: number;
  correct_answers: number;
  wrong_answers: number;
  total_time_spent_seconds: number;
}

export interface RecentActivityItem {
  id: string;
  test_name: string;
  percentage: number;
  attempted_at: string;
}

export interface ProfileHistoryResponse {
  results: TestResult[];
  total: number;
  skip: number;
  limit: number;
}

export async function saveTestResult(
  result: TestResultCreate,
  token: string
): Promise<TestResult> {
  return authFetch(`${API_BASE}/mock-tests/results`, token, {
    method: "POST",
    body: JSON.stringify(result),
  });
}

export async function submitTestResult(
  result: TestSubmitPayload,
  token: string
): Promise<{ result: TestResult; dashboard: unknown; profile: unknown }> {
  return authFetch(`${API_BASE}/tests/submit`, token, {
    method: "POST",
    body: JSON.stringify(result),
  });
}

export async function getTestResults(
  token: string,
  skip: number = 0,
  limit: number = 50
): Promise<TestResult[]> {
  const params = new URLSearchParams({ skip: skip.toString(), limit: limit.toString() });
  return authFetch(`${API_BASE}/mock-tests/results?${params}`, token);
}

export async function getTestResultById(
  resultId: string,
  token: string
): Promise<TestResult> {
  return authFetch(`${API_BASE}/mock-tests/results/${resultId}`, token);
}

export async function deleteTestResult(
  resultId: string,
  token: string
): Promise<{ message: string }> {
  return authFetch(`${API_BASE}/mock-tests/results/${resultId}`, token, {
    method: "DELETE",
  });
}

export async function getAnalytics(token: string): Promise<Analytics> {
  const stats = await authFetch<{
    total_tests_taken?: number;
    total_tests?: number;
    average_score?: number;
    best_score?: number;
    worst_score?: number;
    average_accuracy?: number;
  }>(`${API_BASE}/mock-tests/stats`, token);

  return {
    total_tests: stats.total_tests ?? stats.total_tests_taken ?? 0,
    average_score: stats.average_score ?? 0,
    best_score: stats.best_score ?? 0,
    worst_score: stats.worst_score ?? 0,
    average_accuracy: stats.average_accuracy ?? 0,
  };
}

export async function getProgress(token: string): Promise<ProgressDataPoint[]> {
  return authFetch(`${API_BASE}/mock-tests/progress`, token);
}

export async function getSubjectPerformance(
  token: string
): Promise<SubjectPerformance[]> {
  return authFetch(`${API_BASE}/mock-tests/subject-performance`, token);
}

export async function getTestStats(
  token: string
): Promise<{
  total_tests_taken: number;
  average_score: number;
  best_score: number;
  worst_score: number;
  average_accuracy: number;
}> {
  return authFetch(`${API_BASE}/mock-tests/stats`, token);
}

export async function getProfileOverview(token: string): Promise<ProfileOverview> {
  return authFetch(`${API_BASE}/profile/overview`, token);
}

export async function getProfileHistory(
  token: string,
  params: Record<string, string | number | undefined> = {}
): Promise<ProfileHistoryResponse> {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      query.set(key, String(value));
    }
  });
  return authFetch(`${API_BASE}/profile/test-history?${query.toString()}`, token);
}

export async function getProfileRecentActivity(
  token: string
): Promise<RecentActivityItem[]> {
  return authFetch(`${API_BASE}/profile/recent-activity`, token);
}

export async function getProfilePerformanceTrend(
  token: string
): Promise<ProgressDataPoint[]> {
  return authFetch(`${API_BASE}/profile/performance-trend`, token);
}

export async function getProfileAccuracyTrend(
  token: string
): Promise<AccuracyTrendPoint[]> {
  return authFetch(`${API_BASE}/profile/accuracy-trend`, token);
}

export async function getProfileSubjectPerformance(
  token: string
): Promise<SubjectPerformance[]> {
  return authFetch(`${API_BASE}/profile/subject-performance`, token);
}

export async function getProfileStrengthAnalysis(
  token: string
): Promise<{ 
  strongest_subject: string;
  strongest_score: number;
  weakest_subject: string;
  weakest_score: number;
  top_subjects: SubjectPerformance[];
  bottom_subjects: SubjectPerformance[];
}> {
  return authFetch(`${API_BASE}/profile/strength-analysis`, token);
}

export async function getProfileTestDetails(
  token: string,
  testId: string
): Promise<TestResult> {
  return authFetch(`${API_BASE}/profile/test-details/${testId}`, token);
}
