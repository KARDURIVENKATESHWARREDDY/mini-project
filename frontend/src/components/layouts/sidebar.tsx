"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";
import {
  LayoutDashboard, Search, Shield, Upload, FlaskConical,
  Database, FileSearch, ClipboardList, Users, Settings,
  LogOut, ChevronLeft, Activity, AlertTriangle
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

interface NavItem {
  href: string;
  icon: React.ReactNode;
  label: string;
  roles?: string[];
}

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", icon: <LayoutDashboard className="w-4 h-4" />, label: "Dashboard" },
  { href: "/transactions", icon: <Search className="w-4 h-4" />, label: "Transactions" },
  { href: "/predictions", icon: <Shield className="w-4 h-4" />, label: "Predictions", roles: ["analyst", "admin"] },
  { href: "/batch", icon: <Upload className="w-4 h-4" />, label: "Batch Screening", roles: ["analyst", "admin"] },
  { href: "/evaluation", icon: <FlaskConical className="w-4 h-4" />, label: "Evaluation Lab" },
  { href: "/models", icon: <Database className="w-4 h-4" />, label: "Model Registry" },
  { href: "/investigations", icon: <FileSearch className="w-4 h-4" />, label: "Investigations", roles: ["analyst", "admin"] },
  { href: "/audit", icon: <ClipboardList className="w-4 h-4" />, label: "Audit Logs", roles: ["admin"] },
  { href: "/users", icon: <Users className="w-4 h-4" />, label: "User Management", roles: ["admin"] },
  { href: "/settings", icon: <Settings className="w-4 h-4" />, label: "Settings" },
];

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();

  const visibleItems = NAV_ITEMS.filter(item =>
    !item.roles || !user || item.roles.includes(user.role)
  );

  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 240 }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
      className="relative flex flex-col h-full bg-card border-r border-border/50 overflow-hidden shrink-0"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-14 border-b border-border/50">
        <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center shrink-0">
          <Activity className="w-4 h-4 text-emerald-400" />
        </div>
        <AnimatePresence mode="wait">
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.15 }}
              className="flex flex-col min-w-0"
            >
              <span className="text-sm font-bold text-foreground leading-none">CARD-Net</span>
              <span className="text-[10px] text-muted-foreground truncate">Fraud Intelligence</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Research Banner */}
      {!collapsed && (
        <div className="mx-3 mt-3 px-2.5 py-2 rounded-lg bg-amber-500/10 border border-amber-500/25 flex items-start gap-2">
          <AlertTriangle className="w-3 h-3 text-amber-400 shrink-0 mt-0.5" />
          <p className="text-[10px] text-amber-400/80 leading-tight">
            Research prototype. Not for production fraud blocking.
          </p>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {visibleItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={cn(
                "flex items-center gap-3 px-2.5 py-2 rounded-lg text-sm transition-colors duration-150 group",
                isActive
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              )}
            >
              <span className="shrink-0">{item.icon}</span>
              <AnimatePresence mode="wait">
                {!collapsed && (
                  <motion.span
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.1 }}
                    className="truncate font-medium"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </Link>
          );
        })}
      </nav>

      {/* User + Logout */}
      <div className="border-t border-border/50 p-2">
        {!collapsed && user && (
          <div className="px-2.5 py-2 mb-1">
            <p className="text-xs font-medium text-foreground truncate">{user.full_name}</p>
            <p className="text-[10px] text-muted-foreground truncate">{user.email}</p>
            <span className="inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border/50 uppercase tracking-wide">
              {user.role}
            </span>
          </div>
        )}
        <button
          onClick={logout}
          title="Sign out"
          className="flex items-center gap-3 w-full px-2.5 py-2 rounded-lg text-sm text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors duration-150"
        >
          <LogOut className="w-4 h-4 shrink-0" />
          {!collapsed && <span className="font-medium">Sign out</span>}
        </button>
      </div>

      {/* Collapse toggle */}
      <button
        onClick={onToggle}
        className="absolute top-3.5 -right-3 w-6 h-6 rounded-full bg-card border border-border flex items-center justify-center hover:border-border/80 transition-colors z-10"
      >
        <motion.div animate={{ rotate: collapsed ? 180 : 0 }} transition={{ duration: 0.2 }}>
          <ChevronLeft className="w-3 h-3 text-muted-foreground" />
        </motion.div>
      </button>
    </motion.aside>
  );
}
