"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Eye, EyeOff, Loader2, Shield, Trash2 } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

type Props = {
  compact?: boolean;
};

export default function ApiKeyManager({ compact = false }: Props) {
  const {
    apiKeyLoading,
    apiKeyStatus,
    refreshApiKeyStatus,
    validateUserApiKey,
    saveUserApiKey,
    deleteUserApiKey,
  } = useAuth();
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const hasKey = Boolean(apiKeyStatus?.has_key);
  const router = useRouter();

  useEffect(() => {
    refreshApiKeyStatus().catch(() => undefined);
  }, [refreshApiKeyStatus]);

  async function handleTest() {
    if (!apiKey.trim()) {
      setError("Please enter your Mistral API key first.");
      return;
    }
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      const valid = await validateUserApiKey("mistral", apiKey.trim());
      if (!valid) {
        throw new Error("Invalid API key");
      }
      setMessage("Connection successful. Your key is valid.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to validate key");
    } finally {
      setWorking(false);
    }
  }

  async function handleSave() {
    if (!apiKey.trim()) {
      setError("Please enter your Mistral API key first.");
      return;
    }
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      const valid = await validateUserApiKey("mistral", apiKey.trim());
      if (!valid) {
        throw new Error("Invalid API key");
      }
      await saveUserApiKey("mistral", apiKey.trim());
      setApiKey("");
      setShowKey(false);
      setMessage("Mistral API key saved securely.");
      // Redirect to main app (chat) now that key is configured
      try {
        router.replace("/");
      } catch {
        // ignore navigation errors
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save key");
    } finally {
      setWorking(false);
    }
  }

  async function handleDelete() {
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      await deleteUserApiKey();
      setApiKey("");
      setShowKey(false);
      setMessage("Mistral API key deleted.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete key");
    } finally {
      setWorking(false);
    }
  }

  return (
    <section className="mx-auto w-full max-w-3xl rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-600 dark:text-blue-400">
            AI Settings
          </p>
          <h1 className="mt-2 text-2xl font-semibold">
            Connect Your Mistral Account
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-zinc-400">
            This app uses your own Mistral API key for chat and AI features. Your key is encrypted before it is stored and never shown back in full.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-sm text-slate-700 dark:bg-zinc-900 dark:text-zinc-300">
          <Shield className="h-4 w-4" />
          Mistral
        </div>
      </div>

      {apiKeyLoading ? (
        <div className="mt-6 flex items-center gap-2 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Checking saved key...
        </div>
      ) : null}

      {!apiKeyLoading && hasKey ? (
        <div className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-100">
          <div className="flex items-center gap-2 font-semibold">
            <CheckCircle2 className="h-4 w-4" />
            API key connected
          </div>
          <p className="mt-2">
            Saved key: <span className="font-mono">{apiKeyStatus?.masked_api_key ?? "********"}</span>
          </p>
        </div>
      ) : null}

      <div className={`mt-6 grid gap-4 ${compact ? "md:grid-cols-1" : "md:grid-cols-[1fr_auto]"}`}>
        <label className="block space-y-2 text-sm">
          <span className="font-medium">Mistral API key</span>
          <div className="flex items-center gap-2 rounded-2xl border border-slate-300 bg-slate-50 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900">
            <input
              type={showKey ? "text" : "password"}
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder={hasKey ? "Enter a new key to replace the current one" : "Enter your Mistral API key"}
              className="w-full bg-transparent outline-none placeholder:text-slate-400 dark:placeholder:text-zinc-500"
              autoComplete="off"
              spellCheck={false}
            />
            <button
              type="button"
              onClick={() => setShowKey((value) => !value)}
              className="rounded-full p-1 text-slate-500 hover:bg-slate-200 dark:text-zinc-400 dark:hover:bg-zinc-800"
              title={showKey ? "Hide key" : "Show key"}
            >
              {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </label>

        <div className="flex flex-wrap items-end gap-2">
          <button
            type="button"
            onClick={handleTest}
            disabled={working || !apiKey.trim()}
            className="inline-flex h-11 items-center gap-2 rounded-full border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-800"
          >
            {working ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Test Connection
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={working || !apiKey.trim()}
            className="inline-flex h-11 items-center gap-2 rounded-full bg-blue-600 px-4 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {working ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {hasKey ? "Save Replacement" : "Save Key"}
          </button>
          {hasKey ? (
            <button
              type="button"
              onClick={handleDelete}
              disabled={working}
              className="inline-flex h-11 items-center gap-2 rounded-full border border-rose-200 bg-rose-50 px-4 text-sm font-semibold text-rose-700 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200"
            >
              <Trash2 className="h-4 w-4" />
              Delete Key
            </button>
          ) : null}
        </div>
      </div>

      <div className="mt-5 flex items-start gap-3 rounded-2xl bg-slate-50 p-4 text-sm text-slate-600 dark:bg-zinc-900 dark:text-zinc-400">
        <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-blue-500" />
        <p>
          Create a key in your Mistral account, paste it here, test the connection, and then save it. We only keep the encrypted version on the server.
        </p>
      </div>

      {message ? (
        <p className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-100">
          {message}
        </p>
      ) : null}

      {error ? (
        <p className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
          {error}
        </p>
      ) : null}
    </section>
  );
}
