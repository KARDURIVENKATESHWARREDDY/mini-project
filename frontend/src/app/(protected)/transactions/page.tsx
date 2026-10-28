"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { transactionsApi } from "@/lib/api";
import { RiskBadge, StatusBadge } from "@/components/ui/badges";
import { formatCurrency, formatDate, truncate } from "@/lib/utils";
import { Search, ChevronLeft, ChevronRight, ExternalLink, Filter } from "lucide-react";
import { motion } from "framer-motion";
import Link from "next/link";

const RISK_OPTIONS = ["", "low", "medium", "high"];
const STATUS_OPTIONS = ["", "pending", "under_review", "resolved_fraud", "resolved_legitimate", "dismissed"];

export default function TransactionsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["transactions", page, search, riskFilter, statusFilter],
    queryFn: () =>
      transactionsApi
        .list({
          page,
          page_size: 25,
          search: search || undefined,
          risk_category: riskFilter || undefined,
          review_status: statusFilter || undefined,
        })
        .then((r) => r.data),
  });

  function applySearch() {
    setSearch(searchInput);
    setPage(1);
  }

  const totalPages = data ? Math.ceil(data.total / 25) : 1;

  return (
    <div className="p-6 space-y-5 max-w-[1600px] mx-auto">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-foreground">Transactions</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {data ? `${data.total.toLocaleString()} transactions stored` : "Loading…"}
          </p>
        </div>
        {/* Filters */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <input
              id="tx-search"
              type="text"
              placeholder="Search by ID…"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && applySearch()}
              className="pl-8 pr-4 py-1.5 text-xs bg-muted/50 border border-border/50 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-emerald-500/50 transition-colors w-44"
            />
          </div>
          <select
            id="tx-risk-filter"
            value={riskFilter}
            onChange={(e) => { setRiskFilter(e.target.value); setPage(1); }}
            className="py-1.5 px-2.5 text-xs bg-muted/50 border border-border/50 rounded-lg text-foreground focus:outline-none focus:border-emerald-500/50 transition-colors"
          >
            {RISK_OPTIONS.map((r) => (
              <option key={r} value={r}>{r ? `Risk: ${r}` : "All Risk"}</option>
            ))}
          </select>
          <select
            id="tx-status-filter"
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="py-1.5 px-2.5 text-xs bg-muted/50 border border-border/50 rounded-lg text-foreground focus:outline-none focus:border-emerald-500/50 transition-colors"
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>{s ? `Status: ${s.replace("_", " ")}` : "All Status"}</option>
            ))}
          </select>
          <button
            onClick={applySearch}
            className="flex items-center gap-1.5 py-1.5 px-3 text-xs bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors"
          >
            <Filter className="w-3 h-3" />
            Apply
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="card-glass overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/50 bg-muted/30">
                {["Transaction ID", "Amount", "Time (s)", "Risk", "Probability", "Status", "Label", "Imported", ""].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading
                ? Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i} className="border-b border-border/30">
                      {Array.from({ length: 9 }).map((_, j) => (
                        <td key={j} className="px-4 py-3"><div className="skeleton h-4 w-20" /></td>
                      ))}
                    </tr>
                  ))
                : data?.items.map((tx) => (
                    <motion.tr
                      key={tx.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="border-b border-border/20 hover:bg-muted/20 transition-colors"
                    >
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                        <Link href={`/transactions/${tx.id}`} className="hover:text-emerald-400 hover:underline">
                          {truncate(tx.id, 16)}
                        </Link>
                      </td>
                      <td className="px-4 py-3 font-medium text-foreground">{formatCurrency(tx.amount)}</td>
                      <td className="px-4 py-3 text-muted-foreground">{tx.time_seconds?.toFixed(0) ?? "—"}</td>
                      <td className="px-4 py-3"><RiskBadge risk={tx.risk_category} /></td>
                      <td className="px-4 py-3">
                        {tx.fraud_probability != null ? (
                          <span className={tx.fraud_probability >= 0.7 ? "text-red-400 font-semibold" : tx.fraud_probability >= 0.3 ? "text-amber-400" : "text-emerald-400"}>
                            {(tx.fraud_probability * 100).toFixed(1)}%
                          </span>
                        ) : "—"}
                      </td>
                      <td className="px-4 py-3">
                        {tx.review_status ? <StatusBadge status={tx.review_status} /> : <span className="text-muted-foreground">—</span>}
                      </td>
                      <td className="px-4 py-3">
                        {tx.ground_truth_label != null ? (
                          <span className={tx.ground_truth_label === 1 ? "text-red-400 font-medium" : "text-emerald-400 font-medium"}>
                            {tx.ground_truth_label === 1 ? "Fraud" : "Legit"}
                          </span>
                        ) : <span className="text-muted-foreground">—</span>}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">{formatDate(tx.imported_at)}</td>
                      <td className="px-4 py-3">
                        <Link href={`/transactions/${tx.id}`} className="text-muted-foreground hover:text-emerald-400 transition-colors">
                          <ExternalLink className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </motion.tr>
                  ))}
            </tbody>
          </table>
        </div>
        {/* Pagination */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-border/30">
          <p className="text-xs text-muted-foreground">
            Page {page} of {totalPages} · {data?.total ?? 0} total
          </p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1.5 rounded-lg bg-muted/50 hover:bg-muted disabled:opacity-30 disabled:cursor-not-allowed text-muted-foreground hover:text-foreground transition-colors"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="p-1.5 rounded-lg bg-muted/50 hover:bg-muted disabled:opacity-30 disabled:cursor-not-allowed text-muted-foreground hover:text-foreground transition-colors"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
