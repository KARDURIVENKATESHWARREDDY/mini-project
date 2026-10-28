"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { investigationsApi } from "@/lib/api";
import { StatusBadge } from "@/components/ui/badges";
import { formatDate, formatCurrency } from "@/lib/utils";
import { FileSearch, ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";

const STATUS_OPTIONS = ["", "open", "assigned", "escalated", "resolved", "closed"];

export default function InvestigationsPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["investigations", page, statusFilter],
    queryFn: () =>
      investigationsApi
        .list({ page, page_size: 20, status: statusFilter || undefined })
        .then((r) => r.data),
  });

  const totalPages = data ? Math.ceil(data.total / 20) : 1;

  return (
    <div className="p-6 space-y-5 max-w-6xl mx-auto">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <FileSearch className="w-5 h-5 text-emerald-400" />
            Investigations
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {data ? `${data.total} investigation${data.total !== 1 ? "s" : ""}` : "Loading…"}
          </p>
        </div>
        <select
          id="inv-status-filter"
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="py-1.5 px-2.5 text-xs bg-muted/50 border border-border/50 rounded-lg text-foreground focus:outline-none focus:border-emerald-500/50 transition-colors"
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{s ? `Status: ${s}` : "All Status"}</option>
          ))}
        </select>
      </div>

      <div className="card-glass overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/30 bg-muted/20">
                {["ID", "Transaction", "Status", "Priority", "Amount", "Opened By", "Assigned To", "Opened", ""].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading
                ? Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i} className="border-b border-border/20">
                      {Array.from({ length: 9 }).map((_, j) => (
                        <td key={j} className="px-4 py-3"><div className="skeleton h-4 w-20" /></td>
                      ))}
                    </tr>
                  ))
                : !data?.items.length
                ? (
                    <tr>
                      <td colSpan={9} className="px-4 py-12 text-center text-sm text-muted-foreground">
                        No investigations found.
                      </td>
                    </tr>
                  )
                : data.items.map((inv) => (
                    <motion.tr
                      key={inv.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="border-b border-border/20 hover:bg-muted/20 transition-colors"
                    >
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                        <Link href={`/investigations/${inv.id}`} className="hover:text-emerald-400 hover:underline">
                          {inv.id.slice(0, 8)}…
                        </Link>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                        <Link href={`/transactions/${inv.transaction_id}`} className="hover:text-emerald-400 hover:underline">
                          {inv.transaction_id.slice(0, 8)}…
                        </Link>
                      </td>
                      <td className="px-4 py-3"><StatusBadge status={inv.status} /></td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-medium capitalize ${
                          inv.priority === "critical" ? "text-red-400"
                          : inv.priority === "high" ? "text-amber-400"
                          : inv.priority === "low" ? "text-muted-foreground"
                          : "text-foreground"
                        }`}>
                          {inv.priority}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-foreground font-medium">{formatCurrency(inv.amount)}</td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">{inv.opened_by ?? "—"}</td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">{inv.assigned_to ?? "—"}</td>
                      <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">{formatDate(inv.opened_at)}</td>
                      <td className="px-4 py-3">
                        <Link href={`/investigations/${inv.id}`} className="text-muted-foreground hover:text-emerald-400 transition-colors">
                          <ExternalLink className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </motion.tr>
                  ))}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border/30">
            <p className="text-xs text-muted-foreground">Page {page} of {totalPages}</p>
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
