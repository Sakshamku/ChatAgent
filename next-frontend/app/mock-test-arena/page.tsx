"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../contexts/AuthContext";
import MockTestArena from "../../components/MockTestArena";

export default function MockTestArenaPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
        <div className="rounded-3xl border border-white/10 bg-slate-900/90 px-8 py-6 text-center shadow-2xl shadow-black/20">
          <p className="text-sm uppercase tracking-[0.4em] text-slate-400">Loading Mock Test Arena</p>
          <h1 className="mt-4 text-3xl font-semibold">Please wait while we verify your session.</h1>
        </div>
      </div>
    );
  }

  return <MockTestArena />;
}
