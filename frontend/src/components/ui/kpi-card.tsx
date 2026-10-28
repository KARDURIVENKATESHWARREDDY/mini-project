"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: { value: number; label: string };
  variant?: "default" | "success" | "warning" | "danger";
  loading?: boolean;
}

const variantStyles = {
  default: "border-border/50",
  success: "border-emerald-500/30",
  warning: "border-amber-500/30",
  danger: "border-red-500/30",
};

const iconBgStyles = {
  default: "bg-muted text-muted-foreground",
  success: "bg-emerald-500/10 text-emerald-400",
  warning: "bg-amber-500/10 text-amber-400",
  danger: "bg-red-500/10 text-red-400",
};

export function KpiCard({
  title, value, subtitle, icon, trend, variant = "default", loading = false,
}: KpiCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn(
        "card-glass p-5 flex flex-col gap-4 hover:border-border/80 transition-colors duration-200",
        variantStyles[variant]
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide truncate">
            {title}
          </p>
          {loading ? (
            <div className="skeleton h-8 w-24 mt-1.5" />
          ) : (
            <p className="text-2xl font-bold text-foreground mt-0.5">{value}</p>
          )}
          {subtitle && !loading && (
            <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>
          )}
        </div>
        <div className={cn("p-2.5 rounded-lg shrink-0", iconBgStyles[variant])}>
          {icon}
        </div>
      </div>
      {trend && !loading && (
        <div className="flex items-center gap-1.5 text-xs">
          <span className={cn(
            "font-medium",
            trend.value > 0 ? "text-emerald-400" : trend.value < 0 ? "text-red-400" : "text-muted-foreground"
          )}>
            {trend.value > 0 ? "+" : ""}{trend.value}%
          </span>
          <span className="text-muted-foreground">{trend.label}</span>
        </div>
      )}
    </motion.div>
  );
}
