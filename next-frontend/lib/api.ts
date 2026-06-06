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
