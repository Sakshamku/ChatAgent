"use client";

import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser, login as loginRequest, signup as signupRequest } from "../lib/api";

interface User {
  id: string;
  full_name: string;
  email: string;
  created_at?: string;
}

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (full_name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const STORAGE_KEY = "chatagent_token";

function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(STORAGE_KEY);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const storedToken = getStoredToken();
    if (!storedToken) {
      setLoading(false);
      return;
    }

    getCurrentUser(storedToken)
      .then((data) => {
        setUser(data as User);
        setToken(storedToken);
      })
      .catch(() => {
        window.localStorage.removeItem(STORAGE_KEY);
        setToken(null);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const setSession = (accessToken: string, userPayload: User) => {
    window.localStorage.setItem(STORAGE_KEY, accessToken);
    setToken(accessToken);
    setUser(userPayload);
  };

  const login = async (email: string, password: string) => {
    const response = await loginRequest({ email, password });
    setSession(response.access_token, response.user as User);
    router.replace("/mock-test-arena");
  };

  const signup = async (full_name: string, email: string, password: string) => {
    const response = await signupRequest({ full_name, email, password });
    setSession(response.access_token, response.user as User);
    router.replace("/mock-test-arena");
  };

  const logout = () => {
    window.localStorage.removeItem(STORAGE_KEY);
    setToken(null);
    setUser(null);
    router.push("/login");
  };

  const value = useMemo(
    () => ({ user, token, loading, login, signup, logout }),
    [user, token, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
