"use client";

import React, { useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, FileText, MessageSquare, Plus, Search, Trash2 } from "lucide-react";
import { API_BASE, authFetch } from "../lib/api";
import { useAuth } from "@/contexts/AuthContext";

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
  const { token } = useAuth();

  const loadConversations = useCallback(async (query = "") => {
    if (!token) return;
    setLoading(true);
    try {
      const endpoint = query.trim()
        ? `${API_BASE}/search?query=${encodeURIComponent(query.trim())}`
        : `${API_BASE}/conversations`;
      const data = await authFetch<Conversation[]>(endpoint, token);
      setConversations(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error(error);
      setConversations([]);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    if (!token) return;
    const timer = window.setTimeout(() => {
      loadConversations(searchQuery);
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchQuery, loadConversations, token]);

  async function handleNewChat() {
    try {
      if (!token) return;
      const data = await authFetch<{ thread_id: string }>(`${API_BASE}/conversations`, token, {
        method: "POST",
      });
      onNewChat(data.thread_id);
      await loadConversations(searchQuery);
    } catch (error) {
      console.error(error);
    }
  }

  async function handleDelete(threadId: string, event: React.MouseEvent) {
    event.stopPropagation();
    try {
      if (!token) return;
      const res = await fetch(`${API_BASE}/conversations/${threadId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
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
    <aside
      className={`flex h-full flex-col border-r border-zinc-200 bg-zinc-50 p-4 transition-all duration-300 dark:border-zinc-800 dark:bg-zinc-950 ${
        isCollapsed ? "w-20" : "w-72"
      }`}
    >
      <div className="mb-4 flex items-center justify-between">
        {!isCollapsed ? (
          <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50">Conversations</h2>
        ) : null}
        <button
          type="button"
          onClick={onToggleCollapse}
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="rounded-lg p-2 hover:bg-zinc-200 dark:hover:bg-zinc-800"
        >
          {isCollapsed ? <ChevronRight className="h-5 w-5" /> : <ChevronLeft className="h-5 w-5" />}
        </button>
      </div>

      {!isCollapsed ? (
        <>
          <button
            type="button"
            onClick={handleNewChat}
            className="mb-4 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            New Chat
          </button>

          <label className="mb-4 flex items-center gap-2 rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100">
            <Search className="h-4 w-4 text-zinc-500" />
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-transparent outline-none"
            />
          </label>
        </>
      ) : null}

      <div className="flex-1 overflow-y-auto">
        {loading && !isCollapsed ? (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading...</p>
        ) : null}

        {!loading && conversations.length === 0 && !isCollapsed ? (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">No conversations yet</p>
        ) : null}

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
                  <MessageSquare className="h-5 w-5 text-zinc-500" />
                </div>
              ) : (
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-100">
                      {conversation.title || "Untitled"}
                      {conversation.has_pdf ? (
                        <span className="ml-1 inline-flex align-middle text-zinc-500">
                          <FileText className="h-3.5 w-3.5" />
                        </span>
                      ) : null}
                    </p>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400">
                      {conversation.message_count ?? 0} messages
                    </p>
                  </div>
                  <button
                    type="button"
                    aria-label="Delete conversation"
                    onClick={(e) => handleDelete(conversation.thread_id, e)}
                    className="inline-flex items-center gap-1 text-xs text-red-500 hover:text-red-700"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
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
