"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import Sidebar from "./Sidebar";
import Chat from "./Chat";
import { API_BASE } from "../lib/api";

export default function AppShell() {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    async function initConversation() {
      try {
        const res = await fetch(`${API_BASE}/conversations`);
        if (res.ok) {
          const conversations = await res.json();
          if (Array.isArray(conversations) && conversations.length > 0) {
            setThreadId(conversations[0].thread_id);
            setLoading(false);
            return;
          }
        }

        const createRes = await fetch(`${API_BASE}/conversations`, {
          method: "POST",
        });
        if (createRes.ok) {
          const data = await createRes.json();
          setThreadId(data.thread_id);
        }
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    }

    initConversation();
  }, []);

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
        <header className="flex items-center justify-between border-b border-zinc-200 px-6 py-4 dark:border-zinc-800">
          <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
            AI Assistant
          </h1>
          <Link
            href="/mock-test-arena"
            className="rounded-full border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 transition hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-900"
          >
            Mock Test Arena
          </Link>
        </header>
        <div className="flex-1 overflow-hidden">
          <Chat threadId={threadId} />
        </div>
      </main>
    </div>
  );
}
