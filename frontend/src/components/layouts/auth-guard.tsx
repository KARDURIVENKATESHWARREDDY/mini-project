"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { Activity } from "lucide-react";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore();
  const router = useRouter();
  // Wait for Zustand persist middleware to hydrate from localStorage.
  // On the very first render (SSR + client pre-hydration) isAuthenticated is
  // always false even for logged-in users — we must not redirect at that point.
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    // useEffect only runs on the client, after hydration from localStorage.
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (hydrated && !isAuthenticated) {
      router.replace("/login");
    }
  }, [hydrated, isAuthenticated, router]);

  // Not hydrated yet — show a minimal loading state instead of blank/redirect
  if (!hydrated) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex items-center gap-3 text-muted-foreground">
          <Activity className="w-5 h-5 text-emerald-400 animate-pulse" />
          <span className="text-sm">Loading…</span>
        </div>
      </div>
    );
  }

  // Hydrated but not authenticated — return null while router.replace fires
  if (!isAuthenticated) return null;

  return <>{children}</>;
}

