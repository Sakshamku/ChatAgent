"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { API_BASE } from "@/lib/api";
import {
  deleteApiKey,
  getApiKeyStatus,
  saveApiKey,
  validateApiKey,
  type ApiKeyStatus,
  type ApiProvider,
} from "@/lib/api";

export interface AuthUser {
  id: string;
  full_name: string;
  email: string;
  created_at?: string | null;
}

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  apiKeyLoading: boolean;
  apiKeyStatus: ApiKeyStatus | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (fullName: string, email: string, password: string, confirmPassword?: string) => Promise<void>;
  logout: () => void;
  setSession: (user: AuthUser, token: string) => void;
  refreshApiKeyStatus: () => Promise<void>;
  validateUserApiKey: (provider: ApiProvider, apiKey: string) => Promise<boolean>;
  saveUserApiKey: (provider: ApiProvider, apiKey: string) => Promise<void>;
  deleteUserApiKey: () => Promise<void>;
}

const STORAGE_KEY = "chatagent-auth";

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function loadStoredSession(): { user: AuthUser; token: string } | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { user?: AuthUser; token?: string };
    if (!parsed.user || !parsed.token) return null;
    return { user: parsed.user, token: parsed.token };
  } catch {
    return null;
  }
}

async function authRequest<T>(
  path: string,
  payload: Record<string, string>
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let detail = "Authentication failed";
    try {
      const body = await response.json();
      detail = body?.detail || body?.message || detail;
    } catch {
      detail = await response.text();
    }
    throw new Error(detail);
  }

  return response.json();
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [apiKeyLoading, setApiKeyLoading] = useState(false);
  const [apiKeyStatus, setApiKeyStatus] = useState<ApiKeyStatus | null>(null);

  const persistSession = useCallback((nextUser: AuthUser, nextToken: string) => {
    setUser(nextUser);
    setToken(nextToken);
    // Clear previous user's API key state immediately to avoid showing stale keys
    setApiKeyStatus(null);
    setApiKeyLoading(true);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ user: nextUser, token: nextToken })
      );
    }
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    setApiKeyStatus(null);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  const refreshApiKeyStatus = useCallback(async () => {
    if (!token) {
      setApiKeyStatus(null);
      return;
    }

    setApiKeyLoading(true);
    try {
      const status = await getApiKeyStatus(token);
      setApiKeyStatus(status);
    } catch {
      setApiKeyStatus({ has_key: false, provider: "mistral" });
    } finally {
      setApiKeyLoading(false);
    }
  }, [token]);

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      const stored = loadStoredSession();
      if (!stored) {
        if (!cancelled) setLoading(false);
        return;
      }

      try {
        const response = await fetch(`${API_BASE}/auth/me`, {
          headers: {
            Authorization: `Bearer ${stored.token}`,
          },
        });

        if (!response.ok) {
          throw new Error("Session expired");
        }

        const me = (await response.json()) as AuthUser;
        if (!cancelled) {
          persistSession(me, stored.token);
        }
      } catch {
        if (!cancelled) {
          logout();
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    restoreSession();
    return () => {
      cancelled = true;
    };
  }, [logout, persistSession]);

  useEffect(() => {
    if (!token) {
      setApiKeyStatus(null);
      setApiKeyLoading(false);
      return;
    }

    let cancelled = false;
    setApiKeyLoading(true);

    getApiKeyStatus(token)
      .then((status) => {
        if (!cancelled) {
          setApiKeyStatus(status);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setApiKeyStatus({ has_key: false, provider: "mistral" });
        }
      })
      .finally(() => {
        if (!cancelled) {
          setApiKeyLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  const login = useCallback(
    async (email: string, password: string) => {
      const data = (await authRequest<{ access_token: string; user: AuthUser }>(
        "/auth/login",
        { email, password }
      )) as { access_token: string; user: AuthUser };
      persistSession(data.user, data.access_token);
    },
    [persistSession]
  );

  const signup = useCallback(
    async (fullName: string, email: string, password: string, confirmPassword?: string) => {
      const data = (await authRequest<{ access_token: string; user: AuthUser }>(
        "/auth/signup",
        {
          full_name: fullName,
          email,
          password,
          confirm_password: confirmPassword ?? password,
        }
      )) as { access_token: string; user: AuthUser };
      persistSession(data.user, data.access_token);
    },
    [persistSession]
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      loading,
      apiKeyLoading,
      apiKeyStatus,
      login,
      signup,
      logout,
      setSession: persistSession,
      refreshApiKeyStatus,
      validateUserApiKey: async (provider: ApiProvider, apiKey: string) => {
        if (!token) throw new Error("Session expired. Please sign in again.");
        const result = await validateApiKey(token, provider, apiKey);
        return result.valid;
      },
      saveUserApiKey: async (provider: ApiProvider, apiKey: string) => {
        if (!token) throw new Error("Session expired. Please sign in again.");
        const status = await saveApiKey(token, provider, apiKey);
        setApiKeyStatus(status);
      },
      deleteUserApiKey: async () => {
        if (!token) throw new Error("Session expired. Please sign in again.");
        await deleteApiKey(token);
        setApiKeyStatus({ has_key: false, provider: "mistral" });
      },
    }),
    [
      user,
      token,
      loading,
      apiKeyLoading,
      apiKeyStatus,
      login,
      signup,
      logout,
      persistSession,
      refreshApiKeyStatus,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
