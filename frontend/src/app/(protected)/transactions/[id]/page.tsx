"use client";

import { useQuery } from "@tanstack/react-query";
import { transactionsApi, investigationsApi } from "@/lib/api";
import { RiskBadge, StatusBadge } from "@/components/ui/badges";
import { formatCurrency, formatDate, formatPercent } from "@/lib/utils";
import { ArrowLeft, ExternalLink, AlertTriangle, Search } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { useAuthStore } from "@/store/auth";

export default function TransactionDetailPage() {
  const { user } = useAuthStore();
  const rawParams = useParams();
  const id = (rawParams?.id as string) ?? "";
  const { data: tx, isLoading } = useQuery({
    queryKey: ["transaction", id],
    queryFn: () => transactionsApi.get(id).then((r) => r.data),
    enabled: !!id,
  });

  async function openInvestigation() {
    try {
      await investigationsApi.open(id, "high");
      toast.success("Investigation opened successfully.");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to open investigation.";
      toast.error(msg);
    }
  }

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <div className="skeleton h-6 w-48" />
        <div className="card-glass p-6 space-y-3">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="skeleton h-4 w-full" />)}
        </div>
      </div>
    );
  }

  if (!tx) {
    return (
      <div className="p-6 text-center">
        <p className="text-muted-foreground">Transaction not found.</p>
        <Link href="/transactions" className="text-emerald-400 text-sm mt-2 inline-block hover:underline">← Back to transactions</Link>
      </div>
    );
  }

  const latestPred = tx.predictions?.[0];
  const featureEntries = Object.entries(tx.features ?? {}).filter(([, v]) => v != null);

  return (
    <div className="p-6 space-y-5 max-w-5xl mx-auto">
      <div className="flex items-center gap-3">
        <Link href="/transactions" className="text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <h1 className="text-xl font-bold text-foreground">Transaction Detail</h1>
          <p className="text-xs text-muted-foreground font-mono">{id}</p>
        </div>
        {(user?.role === "admin" || user?.role === "analyst") && !tx.investigation_id && (
          <button
            onClick={openInvestigation}
            className="ml-auto flex items-center gap-1.5 px-3 py-1.5 text-xs bg-amber-500/10 border border-amber-500/30 text-amber-400 rounded-lg hover:bg-amber-500/20 transition-colors"
          >
            <Search className="w-3.5 h-3.5" />
            Open Investigation
          </button>
        )}
        {tx.investigation_id && (
          <Link
            href={`/investigations/${tx.investigation_id}`}
            className="ml-auto flex items-center gap-1.5 px-3 py-1.5 text-xs bg-violet-500/10 border border-violet-500/30 text-violet-400 rounded-lg hover:bg-violet-500/20 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            View Investigation
          </Link>
        )}
      </div>

      {/* Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card-glass p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Amount</p>
          <p className="text-xl font-bold text-foreground">{formatCurrency(tx.amount)}</p>
        </div>
        <div className="card-glass p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Risk</p>
          <RiskBadge risk={latestPred?.risk_category} />
        </div>
        <div className="card-glass p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Fraud Probability</p>
          <p className={`text-xl font-bold ${latestPred?.fraud_probability != null && latestPred.fraud_probability >= 0.7 ? "text-red-400" : "text-foreground"}`}>
            {latestPred ? formatPercent(latestPred.fraud_probability) : "—"}
          </p>
        </div>
        <div className="card-glass p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Ground Truth</p>
          <p className={`text-sm font-semibold ${tx.ground_truth_label === 1 ? "text-red-400" : tx.ground_truth_label === 0 ? "text-emerald-400" : "text-muted-foreground"}`}>
            {tx.ground_truth_label === 1 ? "Fraud" : tx.ground_truth_label === 0 ? "Legitimate" : "Unknown"}
          </p>
        </div>
      </div>

      {/* Prediction History */}
      {tx.predictions && tx.predictions.length > 0 && (
        <div className="card-glass p-5">
          <h2 className="text-sm font-semibold text-foreground mb-3">Prediction History</h2>
          <div className="space-y-2">
            {tx.predictions.map((p: { id: string; risk_category: string; fraud_probability: number; review_status: string; model_name?: string; model_version_id: string; predicted_at: string }) => (
              <div key={p.id} className="flex items-center gap-3 p-3 rounded-lg bg-muted/30 text-xs">
                <RiskBadge risk={p.risk_category} />
                <span className="text-foreground font-semibold">{formatPercent(p.fraud_probability)}</span>
                <StatusBadge status={p.review_status} />
                <span className="text-muted-foreground">{p.model_name ?? p.model_version_id.slice(0, 8)}</span>
                <span className="ml-auto text-muted-foreground">{formatDate(p.predicted_at)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SHAP values */}
      {latestPred?.shap_values && (
        <div className="card-glass p-5">
          <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            Feature Attributions (SHAP)
          </h2>
          <div className="space-y-1.5">
            {(() => {
              const shap = (latestPred.shap_values ?? {}) as Record<string, number>;
              const entries = Object.entries(shap);
              const maxAbsVal = entries.length ? Math.max(...entries.map(([, v]) => Math.abs(Number(v)))) : 1;
              return entries
                .sort(([, a], [, b]) => Math.abs(Number(b)) - Math.abs(Number(a)))
                .slice(0, 15)
                .map(([feat, rawVal]) => {
                  const val = Number(rawVal);
                  const pct = maxAbsVal ? (Math.abs(val) / maxAbsVal) * 100 : 0;
                  return (
                    <div key={feat} className="flex items-center gap-2 text-xs">
                      <span className="w-12 text-muted-foreground font-mono text-right shrink-0">{feat}</span>
                      <div className="flex-1 h-4 bg-muted/30 rounded overflow-hidden">
                        <div
                          className="h-full rounded transition-all"
                          style={{
                            width: `${pct}%`,
                            background: val > 0 ? "#ef4444" : "#10b981",
                            opacity: 0.7,
                          }}
                        />
                      </div>
                      <span className={`w-16 text-right font-mono shrink-0 ${val > 0 ? "text-red-400" : "text-emerald-400"}`}>
                        {val > 0 ? "+" : ""}{val.toFixed(4)}
                      </span>
                    </div>
                  );
                });
            })()}
          </div>
          <p className="text-[10px] text-muted-foreground mt-2">Red = pushes towards fraud; Green = pushes towards legitimate.</p>
        </div>
      )}

      {/* Raw features */}
      <div className="card-glass p-5">
        <h2 className="text-sm font-semibold text-foreground mb-3">PCA Feature Vector</h2>
        <div className="grid grid-cols-4 md:grid-cols-7 gap-2">
          {featureEntries.map(([k, v]) => (
            <div key={k} className="p-2 rounded-lg bg-muted/30 text-center">
              <p className="text-[10px] text-muted-foreground uppercase">{k}</p>
              <p className="text-xs font-mono text-foreground mt-0.5">{(v as number).toFixed(3)}</p>
            </div>
          ))}
        </div>
      </div>

      <p className="text-[10px] text-muted-foreground">Imported: {formatDate(tx.imported_at)}</p>
    </div>
  );
}
