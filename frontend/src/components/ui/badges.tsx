"use client";

import { cn } from "@/lib/utils";
import { getRiskBadgeClass } from "@/lib/utils";
import { AlertTriangle, CheckCircle, MinusCircle } from "lucide-react";

interface RiskBadgeProps {
  risk: string | null | undefined;
  showIcon?: boolean;
  className?: string;
}

const riskIcons = {
  high: <AlertTriangle className="w-3 h-3" />,
  medium: <MinusCircle className="w-3 h-3" />,
  low: <CheckCircle className="w-3 h-3" />,
};

export function RiskBadge({ risk, showIcon = true, className }: RiskBadgeProps) {
  if (!risk) return <span className="text-muted-foreground text-xs">—</span>;
  const normalised = risk.toLowerCase() as "high" | "medium" | "low";
  return (
    <span className={cn(getRiskBadgeClass(normalised), "gap-1", className)}>
      {showIcon && riskIcons[normalised]}
      {risk.charAt(0).toUpperCase() + risk.slice(1)}
    </span>
  );
}

interface StatusBadgeProps {
  status: string;
  className?: string;
}

const STATUS_MAP: Record<string, { label: string; cls: string }> = {
  pending: { label: "Pending", cls: "bg-muted/80 text-muted-foreground border border-border/50" },
  under_review: { label: "Under Review", cls: "bg-amber-500/15 text-amber-400 border border-amber-500/30" },
  resolved_fraud: { label: "Confirmed Fraud", cls: "bg-red-500/15 text-red-400 border border-red-500/30" },
  resolved_legitimate: { label: "Legitimate", cls: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30" },
  dismissed: { label: "Dismissed", cls: "bg-muted/60 text-muted-foreground border border-border/30" },
  open: { label: "Open", cls: "bg-blue-500/15 text-blue-400 border border-blue-500/30" },
  assigned: { label: "Assigned", cls: "bg-violet-500/15 text-violet-400 border border-violet-500/30" },
  escalated: { label: "Escalated", cls: "bg-red-500/15 text-red-400 border border-red-500/30" },
  resolved: { label: "Resolved", cls: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30" },
  closed: { label: "Closed", cls: "bg-muted/60 text-muted-foreground border border-border/30" },
  completed: { label: "Completed", cls: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30" },
  processing: { label: "Processing", cls: "bg-blue-500/15 text-blue-400 border border-blue-500/30" },
  queued: { label: "Queued", cls: "bg-muted/60 text-muted-foreground border border-border/30" },
  failed: { label: "Failed", cls: "bg-red-500/15 text-red-400 border border-red-500/30" },
  running: { label: "Running", cls: "bg-blue-500/15 text-blue-400 border border-blue-500/30" },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_MAP[status] || { label: status, cls: "bg-muted text-muted-foreground" };
  return (
    <span className={cn(
      "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
      config.cls, className
    )}>
      {config.label}
    </span>
  );
}
