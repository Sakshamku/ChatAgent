"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot, Brain, LogOut, Settings, User } from "lucide-react";
import Sidebar from "./Sidebar";
import Chat from "./Chat";
import { API_BASE, authFetch } from "../lib/api";
import { useAuth } from "@/contexts/AuthContext";

export default function AppShell() {
  const { user, token, logout } = useAuth();
  const pathname = usePathname();
  const [threadId, setThreadId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const isMockActive = pathname === "/mock-test-arena";
  const isSettingsActive = pathname === "/settings";
  const navButtonClass = (active: boolean) =>
    `inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm font-medium transition duration-200 hover:-translate-y-0.5 hover:shadow-sm focus:outline-none focus:ring-2 focus:ring-zinc-400 focus:ring-offset-2 dark:focus:ring-offset-zinc-950 ${
      active
        ? "border-zinc-900 bg-zinc-900 text-white shadow-sm dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900"
        : "border-zinc-200 bg-white/80 text-zinc-700 hover:border-zinc-300 hover:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-900/80 dark:text-zinc-200 dark:hover:border-zinc-600 dark:hover:bg-zinc-800"
    }`;

  useEffect(() => {
    async function initConversation() {
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const conversations = await authFetch<Array<{ thread_id: string }>>(
          `${API_BASE}/conversations`,
          token
        );
        if (Array.isArray(conversations) && conversations.length > 0) {
          setThreadId(conversations[0].thread_id);
          setLoading(false);
          return;
        }

        const created = await authFetch<{ thread_id: string }>(
          `${API_BASE}/conversations`,
          token,
          {
            method: "POST",
          }
        );
        if (created?.thread_id) {
          setThreadId(created.thread_id);
        }
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    }

    initConversation();
  }, [token]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center text-zinc-500">
        Loading...
      </div>
    );
  }

  if (!threadId) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-3 px-6 text-center text-zinc-500">
        <p className="text-lg font-medium text-zinc-700 dark:text-zinc-300">
          Cannot connect to the backend API
        </p>
        <p className="max-w-md text-sm">
          Start the API server from the project root, then restart the Next.js dev server:
        </p>
        <code className="rounded bg-zinc-100 px-3 py-2 text-xs dark:bg-zinc-900">
          myvnv\Scripts\uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000
        </code>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-white dark:bg-black">
      <Sidebar
        activeThreadId={threadId}
        onSelectThread={setThreadId}
        onNewChat={setThreadId}
        isCollapsed={isCollapsed}
        onToggleCollapse={() => setIsCollapsed(!isCollapsed)}
      />
      <main className="flex flex-1 flex-col">
        <header className="border-b border-zinc-200 bg-white/80 px-4 py-3 backdrop-blur-sm sm:px-6 sm:py-4 dark:border-zinc-800 dark:bg-zinc-950/80">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-zinc-900 text-white shadow-sm ring-1 ring-zinc-200 dark:bg-zinc-100 dark:text-zinc-900 dark:ring-zinc-700">
                <Bot className="h-5 w-5" aria-hidden="true" />
              </div>
              <div className="flex flex-col">
                <h1 className="text-lg font-semibold tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-xl">
                  AI Assistant
                </h1>
                <div className="flex items-center gap-1.5 text-sm text-zinc-500 dark:text-zinc-400">
                  <User className="h-4 w-4" aria-hidden="true" />
                  <span>
                    {user?.full_name ? `Signed in as ${user.full_name}` : "Welcome back"}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 sm:gap-2.5">
              <Link
                href="/mock-test-arena"
                aria-label="Open mock test arena"
                className={navButtonClass(isMockActive)}
              >
                <Brain className="h-4 w-4" aria-hidden="true" />
                <span className="text-sm sm:text-[15px]">Mock Test Arena</span>
              </Link>
              <Link
                href="/settings"
                aria-label="Open AI settings"
                className={navButtonClass(isSettingsActive)}
              >
                <Settings className="h-4 w-4" aria-hidden="true" />
                <span className="text-sm sm:text-[15px]">AI Settings</span>
              </Link>
              <button
                type="button"
                onClick={logout}
                aria-label="Log out"
                className={navButtonClass(false)}
              >
                <LogOut className="h-4 w-4" aria-hidden="true" />
                <span className="text-sm sm:text-[15px]">Logout</span>
              </button>
            </div>
          </div>
        </header>
        <div className="flex-1 overflow-hidden">
          <Chat threadId={threadId} />
        </div>
      </main>
    </div>
  );
}
