"use client";

import React, { useCallback, useEffect, useState } from "react";
import { API_BASE } from "../lib/api";

export interface Conversation {
  thread_id: string;
  title: string;
  message_count?: number;
  updated_at?: string;
  has_pdf?: boolean;
  document?: { filename?: string };
}

interface SidebarProps {
  activeThreadId: string | null;
  onSelectThread: (threadId: string) => void;
  onNewChat: (threadId: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export default function Sidebar({
  activeThreadId,
  onSelectThread,
  onNewChat,
  isCollapsed,
  onToggleCollapse,
}: SidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);

  const loadConversations = useCallback(async (query = "") => {
    setLoading(true);
    try {
      const endpoint = query.trim()
        ? `${API_BASE}/search?query=${encodeURIComponent(query.trim())}`
        : `${API_BASE}/conversations`;
      const res = await fetch(endpoint);
      if (!res.ok) throw new Error("Failed to load conversations");
      const data = await res.json();
      setConversations(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error(error);
      setConversations([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadConversations(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, loadConversations]);

  async function handleNewChat() {
    try {
      const res = await fetch(`${API_BASE}/conversations`, { method: "POST" });
      if (!res.ok) throw new Error("Failed to create conversation");
      const data = await res.json();
      onNewChat(data.thread_id);
      await loadConversations(searchQuery);
    } catch (error) {
      console.error(error);
    }
  }

  async function handleDelete(threadId: string, event: React.MouseEvent) {
    event.stopPropagation();
    try {
      const res = await fetch(`${API_BASE}/conversations/${threadId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete conversation");
      if (activeThreadId === threadId) {
        await handleNewChat();
      } else {
        await loadConversations(searchQuery);
      }
    } catch (error) {
      console.error(error);
    }
  }

  return (
    <aside className={`flex h-full flex-col border-r border-zinc-200 bg-zinc-50 p-4 transition-all duration-300 dark:border-zinc-800 dark:bg-zinc-950 ${
      isCollapsed ? "w-20" : "w-72"
    }`}>
      <div className="mb-4 flex items-center justify-between">
        {!isCollapsed && (
          <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50">
            Conversations
          </h2>
        )}
        <button
          type="button"
          onClick={onToggleCollapse}
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="rounded-lg p-2 hover:bg-zinc-200 dark:hover:bg-zinc-800"
        >
          {isCollapsed ? (
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          ) : (
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          )}
        </button>
      </div>

      {!isCollapsed && (
        <>
          <button
            type="button"
            onClick={handleNewChat}
            className="mb-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            New Chat
          </button>

          <input
            type="text"
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="mb-4 w-full rounded-lg border border-zinc-300 bg-white p-2 text-sm dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
          />
        </>
      )}

      <div className="flex-1 overflow-y-auto">
        {loading && !isCollapsed && (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading...</p>
        )}

        {!loading && conversations.length === 0 && !isCollapsed && (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            No conversations yet
          </p>
        )}

        {conversations.map((conversation) => {
          const isActive = conversation.thread_id === activeThreadId;
          return (
            <div
              key={conversation.thread_id}
              role="button"
              tabIndex={0}
              onClick={() => onSelectThread(conversation.thread_id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  onSelectThread(conversation.thread_id);
                }
              }}
              className={`mb-2 cursor-pointer rounded-lg border px-3 py-2 transition-colors ${
                isActive
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-950/40"
                  : "border-transparent hover:bg-zinc-100 dark:hover:bg-zinc-900"
              }`}
              title={isCollapsed ? conversation.title : undefined}
            >
              {isCollapsed ? (
                <div className="flex items-center justify-center">
                  <span className="text-lg">💬</span>
                </div>
              ) : (
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-100">
                      {conversation.title || "Untitled"}
                      {conversation.has_pdf ? " 📄" : ""}
                    </p>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400">
                      {conversation.message_count ?? 0} messages
                    </p>
                  </div>
                  <button
                    type="button"
                    aria-label="Delete conversation"
                    onClick={(e) => handleDelete(conversation.thread_id, e)}
                    className="text-xs text-red-500 hover:text-red-700"
                  >
                    Delete
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
}
