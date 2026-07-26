"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import MockTestArena from "../../components/MockTestArena";
import { useAuth } from "@/contexts/AuthContext";

export default function MockTestArenaPage() {
  const { token, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !token) {
      router.replace("/login");
    }
  }, [loading, router, token]);

  if (loading || !token) {
    return null;
  }

  return <MockTestArena />;
}
