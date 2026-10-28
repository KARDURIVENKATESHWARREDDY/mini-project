"use client";

import { useState } from "react";
import { Sidebar } from "./sidebar";
import { Bell, Search } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { motion } from "framer-motion";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [collapsed, setCollapsed] = useState(false);
  const { user } = useAuthStore();

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Top header */}
        <header className="h-14 border-b border-border/50 bg-card/50 backdrop-blur-sm flex items-center px-6 gap-4 shrink-0">
          {/* Search placeholder */}
          <div className="flex items-center gap-2 flex-1 max-w-md">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search transactions, cases…"
                className="w-full pl-9 pr-4 py-1.5 text-sm bg-muted/50 border border-border/50 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-emerald-500/50 focus:bg-muted transition-colors"
              />
            </div>
          </div>
          <div className="flex items-center gap-3 ml-auto">
            <button className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center hover:bg-muted/80 transition-colors relative">
              <Bell className="w-4 h-4 text-muted-foreground" />
              <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-emerald-400" />
            </button>
            <div className="w-8 h-8 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
              <span className="text-xs font-bold text-emerald-400">
                {user?.full_name?.charAt(0).toUpperCase() ?? "U"}
              </span>
            </div>
          </div>
        </header>
        {/* Main content */}
        <main className="flex-1 overflow-auto">
          <motion.div
            key="page"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            {children}
          </motion.div>
        </main>
      </div>
    </div>
  );
}
