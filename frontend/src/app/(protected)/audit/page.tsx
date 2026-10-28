"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { auditApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { ClipboardList, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { motion } from "framer-motion";

const ACTION_CATEGORIES = [
  "", "user.", "prediction.", "batch.", "investigation.", "model.", "evaluation.",
];

export default function AuditPage() {
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState("");
  const [emailFilter, setEmailFilter] = useState("");
  const [emailInput, setEmailInput] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["audit", page, actionFilter, emailFilter],
    queryFn: () =>
      auditApi.list({
        page,
        page_size: 50,
        action: actionFilter || undefined,
        actor_email: emailFilter || undefined,
      }).then((r) => r.data),
  });

  const totalPages = data ? Math.ceil(data.total / 50) : 1;

  const actionColors: Record<string, string> = {
    "user.login": "text-emerald-400",
    "user.logout": "text-muted-foreground",
    "user.created": "text-blue-400",
    "prediction.created": "text-violet-400",
    "batch.uploaded": "text-amber-400",
    "model.activated": "text-emerald-400",
    "investigation.opened": "text-amber-400",
    "investigation.resolve_fraud": "text-red-400",
    "investigation.resolve_legitimate": "text-emerald-400",
    "evaluation.triggered": "text-blue-400",
  };

  return (
    <div className="p-6 space-y-5 max-w-6xl mx-auto">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <ClipboardList className="w-5 h-5 text-emerald-400" />
            Audit Log
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Immutable record of all system actions. {data ? `${data.total.toLocaleString()} events` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select
            id="audit-action-filter"
            value={actionFilter}
            onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
            className="py-1.5 px-2.5 text-xs bg-muted/50 border border-border/50 rounded-lg text-foreground focus:outline-none focus:border-emerald-500/50 transition-colors"
          >
            {ACTION_CATEGORIES.map((a) => (
              <option key={a} value={a}>{a ? `Action: ${a}*` : "All Actions"}</option>
            ))}
          </select>
          <div className="flex items-center gap-1">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
              <input
                id="audit-email-filter"
                type="text"
                placeholder="Filter by email…"
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { setEmailFilter(emailInput); setPage(1); }}}
                className="pl-8 pr-4 py-1.5 text-xs bg-muted/50 border border-border/50 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-emerald-500/50 transition-colors w-44"
              />
            </div>
            <button
              onClick={() => { setEmailFilter(emailInput); setPage(1); }}
              className="text-xs px-2.5 py-1.5 bg-muted hover:bg-muted/80 text-muted-foreground rounded-lg transition-colors border border-border/50"
            >
              Apply
            </button>
          </div>
        </div>
      </div>

      <div className="card-glass overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/30 bg-muted/20">
                {["Time", "Actor", "Action", "Resource Type", "Resource ID", "IP Address", "Details"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading
                ? Array.from({ length: 10 }).map((_, i) => (
                    <tr key={i} className="border-b border-border/20">
                      {Array.from({ length: 7 }).map((_, j) => (
                        <td key={j} className="px-4 py-3"><div className="skeleton h-4 w-20" /></td>
                      ))}
                    </tr>
                  ))
                : !data?.items.length
                ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-12 text-center text-sm text-muted-foreground">
                        No audit events found.
                      </td>
                    </tr>
                  )
                : data.items.map((ev) => (
                    <motion.tr
                      key={ev.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="border-b border-border/20 hover:bg-muted/20 transition-colors"
                    >
                      <td className="px-4 py-2.5 text-xs text-muted-foreground whitespace-nowrap">{formatDate(ev.created_at)}</td>
                      <td className="px-4 py-2.5 text-xs text-foreground">{ev.actor_email ?? <span className="text-muted-foreground">system</span>}</td>
                      <td className="px-4 py-2.5 text-xs font-mono">
                        <span className={actionColors[ev.action] ?? "text-muted-foreground"}>{ev.action}</span>
                      </td>
                      <td className="px-4 py-2.5 text-xs text-muted-foreground">{ev.resource_type ?? "—"}</td>
                      <td className="px-4 py-2.5 text-xs font-mono text-muted-foreground">{ev.resource_id ? ev.resource_id.slice(0, 12) + "…" : "—"}</td>
                      <td className="px-4 py-2.5 text-xs text-muted-foreground">{ev.ip_address ?? "—"}</td>
                      <td className="px-4 py-2.5 text-xs text-muted-foreground max-w-[200px] truncate">
                        {ev.extra ? JSON.stringify(ev.extra) : "—"}
                      </td>
                    </motion.tr>
                  ))}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border/30">
            <p className="text-xs text-muted-foreground">Page {page} of {totalPages} · {data?.total.toLocaleString()} events</p>
            <div className="flex items-center gap-1">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="p-1.5 rounded-lg bg-muted/50 hover:bg-muted disabled:opacity-30 text-muted-foreground hover:text-foreground transition-colors">
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages} className="p-1.5 rounded-lg bg-muted/50 hover:bg-muted disabled:opacity-30 text-muted-foreground hover:text-foreground transition-colors">
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
