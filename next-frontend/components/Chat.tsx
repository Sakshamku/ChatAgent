"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  FileText,
  Loader2,
  MessagesSquare,
  Plus,
  SendHorizontal,
  X,
} from "lucide-react";
import { API_BASE } from "../lib/api";
import { useTypewriter } from "../hooks/useTypewriter";
import MarkdownMessage from "./MarkdownMessage";
import StreamingText from "./StreamingText";

interface Message {
  role: "user" | "assistant";
  content: string;
  id: string;
  isComplete?: boolean;
}

interface ApiMessage {
  role: string;
  content: string;
}

interface UploadedFile {
  name: string;
  pages?: number;
  chunks?: number;
}

function parseSseChunk(raw: string): string | null {
  const line = raw.trim();
  if (!line.startsWith("data:")) return null;

  const data = line.slice(5).trim();
  if (!data || data === "[DONE]") return null;

  try {
    const parsed = JSON.parse(data) as { token?: string; error?: string };
    if (parsed.error) throw new Error(parsed.error);
    return parsed.token ?? null;
  } catch (error) {
    if (data.startsWith("{")) throw error;
    return data;
  }
}

export default function Chat({ threadId }: { threadId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(
    null
  );
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>(
    {}
  );
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fullContentRef = useRef("");
  const typewriter = useTypewriter();

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typewriter.displayed, isStreaming]);

  useEffect(() => {
    async function fetchMessages() {
      if (!threadId) return;
      try {
        const res = await fetch(`${API_BASE}/messages/${threadId}`);
        if (!res.ok) throw new Error("Failed to load messages");
        const data: ApiMessage[] = await res.json();
        const loaded = data.map((msg, idx) => ({
          role:
            msg.role === "assistant"
              ? ("assistant" as const)
              : ("user" as const),
          content: msg.content,
          id: `msg-${idx}`,
          isComplete: true,
        }));
        setMessages(loaded);
      } catch (error) {
        console.error(error);
        setMessages([]);
      }
    }

    fetchMessages();
  }, [threadId]);

  useEffect(() => {
    async function fetchMetadata() {
      if (!threadId) return;
      setUploadedFiles([]);
      setUploadError(null);

      try {
        const res = await fetch(`${API_BASE}/metadata/${threadId}`);
        if (!res.ok) return;
        const data = await res.json();
        if (data?.filename) {
          setUploadedFiles([
            {
              name: data.filename,
              pages: data.documents,
              chunks: data.chunks,
            },
          ]);
        }
      } catch (error) {
        console.error(error);
      }
    }

    fetchMetadata();
  }, [threadId]);

  const sendMessage = async (overrideMessage?: string) => {
    const messageText = (overrideMessage ?? input).trim();
    if (!messageText || isStreaming || !threadId) return;

    const userMsg: Message = {
      role: "user",
      content: messageText,
      id: `msg-${Date.now()}`,
      isComplete: true,
    };
    setMessages((prev) => [...prev, userMsg]);
    if (!overrideMessage) {
      setInput("");
    }
    setIsStreaming(true);

    const assistantId = `msg-assist-${Date.now()}`;
    setStreamingMessageId(assistantId);
    fullContentRef.current = "";
    typewriter.reset();

    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "", id: assistantId, isComplete: false },
    ]);

    try {
      const response = await fetch(
        `${API_BASE}/conversations/${threadId}/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify({ message: userMsg.content }),
          cache: "no-store",
        }
      );

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      if (!response.body) {
        throw new Error("No response body");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";

        for (const event of events) {
          for (const line of event.split("\n")) {
            const token = parseSseChunk(line);
            if (token) {
              fullContentRef.current += token;
              typewriter.append(token);
            }
          }
        }
      }

      if (buffer.trim()) {
        for (const line of buffer.split("\n")) {
          const token = parseSseChunk(line);
          if (token) {
            fullContentRef.current += token;
            typewriter.append(token);
          }
        }
      }

      await typewriter.waitUntilDone();

      const finalContent = fullContentRef.current;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: finalContent, isComplete: true }
            : m
        )
      );
    } catch (error) {
      console.error(error);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                content: "Sorry, something went wrong. Please try again.",
                isComplete: true,
              }
            : m
        )
      );
    } finally {
      setIsStreaming(false);
      setStreamingMessageId(null);
      typewriter.reset();
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  const startMockInterview = () => {
    sendMessage(
      "Start a mixed mock interview for a software engineer role using my uploaded resume projects and my weakest DSA topics. Ask me one question at a time and score my answer after I respond."
    );
  };

  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    if (!event.target.files || !threadId) return;

    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    const invalidFile = files.find(
      (file) =>
        file.type !== "application/pdf" &&
        !file.name.toLowerCase().endsWith(".pdf")
    );
    if (invalidFile) {
      setUploadError("Only PDF files can be uploaded for chat context.");
      event.target.value = "";
      return;
    }

    setUploadError(null);
    setIsUploading(true);
    try {
      for (const file of files) {
        setUploadProgress((prev) => ({ ...prev, [file.name]: 0 }));

        const formData = new FormData();
        formData.append("file", file);
        formData.append("thread_id", threadId);
        formData.append("filename", file.name);

        const progressInterval = setInterval(() => {
          setUploadProgress((prev) => ({
            ...prev,
            [file.name]: Math.min((prev[file.name] || 0) + Math.random() * 30, 90),
          }));
        }, 200);

        const response = await fetch(`${API_BASE}/pdf`, {
          method: "POST",
          body: formData,
        });

        clearInterval(progressInterval);

        if (!response.ok) {
          const detail = await response.json().catch(() => null);
          throw new Error(detail?.detail ?? `Failed to upload ${file.name}`);
        }

        const meta = await response.json();
        setUploadProgress((prev) => ({ ...prev, [file.name]: 100 }));
        setUploadedFiles((prev) => [
          ...prev.filter((item) => item.name !== file.name),
          {
            name: meta.filename ?? file.name,
            pages: meta.documents,
            chunks: meta.chunks,
          },
        ]);

        setTimeout(() => {
          setUploadProgress((prev) => {
            const newProgress = { ...prev };
            delete newProgress[file.name];
            return newProgress;
          });
        }, 500);
      }
    } catch (error) {
      console.error("Upload failed:", error);
      setUploadError(
        error instanceof Error
          ? error.message
          : "Failed to upload file. Please try again."
      );
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <div className="flex h-full flex-col bg-white dark:bg-zinc-950">
      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
        {messages.length === 0 && (
          <div className="mx-auto max-w-3xl py-16 text-center text-zinc-500 dark:text-zinc-400">
            <h3 className="mb-2 text-lg font-semibold text-zinc-800 dark:text-zinc-200">
              Start a conversation
            </h3>
            <p className="text-sm">
              Ask anything - coding, PDFs, data analysis, and more.
            </p>
          </div>
        )}

        <div className="mx-auto flex max-w-3xl flex-col gap-6">
          {messages.map((msg) => {
            const isAssistant = msg.role === "assistant";
            const isActiveStream = isStreaming && msg.id === streamingMessageId;

            return (
              <div
                key={msg.id}
                className={`flex gap-3 ${isAssistant ? "" : "flex-row-reverse"}`}
              >
                <div
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${
                    isAssistant
                      ? "bg-green-600 text-white"
                      : "bg-blue-600 text-white"
                  }`}
                >
                  {isAssistant ? "AI" : "You"}
                </div>

                <div
                  className={`min-w-0 flex-1 rounded-2xl px-4 py-3 ${
                    isAssistant
                      ? "bg-zinc-50 text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100"
                      : "bg-blue-600 text-white"
                  }`}
                >
                  {isAssistant ? (
                    isActiveStream || !msg.isComplete ? (
                      <StreamingText
                        content={typewriter.displayed}
                        showCursor={isActiveStream}
                      />
                    ) : (
                      <MarkdownMessage content={msg.content} />
                    )
                  ) : (
                    <p className="whitespace-pre-wrap text-[15px] leading-relaxed">
                      {msg.content}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
        <div ref={chatEndRef} />
      </div>

      <div className="border-t border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
        <div className="mx-auto max-w-3xl">
          <div className="rounded-3xl border border-zinc-300 bg-zinc-50 p-2 shadow-sm focus-within:border-zinc-400 dark:border-zinc-700 dark:bg-zinc-900 dark:focus-within:border-zinc-500">
            {(uploadedFiles.length > 0 ||
              Object.keys(uploadProgress).length > 0) && (
              <div className="flex flex-wrap gap-2 px-2 pb-2">
                {uploadedFiles.map((file) => (
                  <div
                    key={file.name}
                    className="flex max-w-full items-center gap-2 rounded-2xl border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
                  >
                    <FileText
                      className="h-4 w-4 shrink-0 text-red-500"
                      aria-hidden="true"
                    />
                    <span className="truncate">{file.name}</span>
                    {file.pages ? (
                      <span className="shrink-0 text-zinc-400">
                        {file.pages}p
                      </span>
                    ) : null}
                    <button
                      type="button"
                      onClick={() =>
                        setUploadedFiles((prev) =>
                          prev.filter((item) => item.name !== file.name)
                        )
                      }
                      className="rounded-full p-0.5 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-700 dark:hover:text-zinc-100"
                      title="Hide attachment"
                    >
                      <X className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  </div>
                ))}
                {Object.entries(uploadProgress).map(([name, progress]) => (
                  <div
                    key={name}
                    className="flex max-w-full items-center gap-2 rounded-2xl border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
                  >
                    <Loader2
                      className="h-4 w-4 shrink-0 animate-spin text-zinc-500"
                      aria-hidden="true"
                    />
                    <span className="truncate">{name}</span>
                    <span className="shrink-0 text-zinc-400">
                      {Math.round(progress)}%
                    </span>
                  </div>
                ))}
              </div>
            )}

            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={2}
              className="max-h-40 min-h-14 w-full resize-none bg-transparent px-3 py-2 text-[15px] leading-relaxed text-zinc-900 outline-none placeholder:text-zinc-500 dark:text-zinc-100"
              placeholder="Message AI Assistant..."
              disabled={isStreaming}
            />

            <div className="flex items-center justify-between px-1 pb-1">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isStreaming || isUploading}
                  title="Upload PDF"
                  className="flex h-9 w-9 items-center justify-center rounded-full border border-zinc-300 bg-white text-zinc-700 transition hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
                >
                  {isUploading ? (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  ) : (
                    <Plus className="h-5 w-5" aria-hidden="true" />
                  )}
                </button>

                <button
                  type="button"
                  onClick={startMockInterview}
                  disabled={isStreaming}
                  title="Start mock interview"
                  className="flex h-9 items-center gap-2 rounded-full border border-zinc-300 bg-white px-3 text-xs font-medium text-zinc-700 transition hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
                >
                  <MessagesSquare className="h-4 w-4" aria-hidden="true" />
                  <span>Mock Interview</span>
                </button>
              </div>

              <button
                type="button"
                onClick={() => sendMessage()}
                disabled={isStreaming || !input.trim()}
                title="Send message"
                className="flex h-9 w-9 items-center justify-center rounded-full bg-zinc-900 text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:bg-zinc-300 dark:bg-zinc-100 dark:text-zinc-950 dark:hover:bg-zinc-300 dark:disabled:bg-zinc-700 dark:disabled:text-zinc-400"
              >
                {isStreaming ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <SendHorizontal className="h-4 w-4" aria-hidden="true" />
                )}
              </button>
            </div>
          </div>

          {uploadError ? (
            <p className="mt-2 px-3 text-xs text-red-600 dark:text-red-400">
              {uploadError}
            </p>
          ) : null}
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf,.pdf"
          onChange={handleFileUpload}
          style={{ display: "none" }}
        />
      </div>
    </div>
  );
}
