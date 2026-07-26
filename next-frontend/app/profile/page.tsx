"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import ProfileDashboard from "@/components/ProfileDashboard";
import { useAuth } from "@/contexts/AuthContext";

export default function ProfilePage() {
  const { token, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !token) {
      router.replace("/login");
    }
  }, [loading, token, router]);

  if (loading || !token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-500 dark:bg-zinc-950">
        Loading profile...
      </div>
    );
  }

  return <ProfileDashboard />;
}
