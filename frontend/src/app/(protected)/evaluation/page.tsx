"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { evaluationApi } from "@/lib/api";
import { StatusBadge } from "@/components/ui/badges";
import { formatDate, formatPercent } from "@/lib/utils";
import { FlaskConical, Play, RefreshCw, TrendingUp, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { useAuthStore } from "@/store/auth";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend,
} from "recharts";
import { motion } from "framer-motion";

export default function EvaluationPage() {
  const { user } = useAuthStore();
  const qc = useQueryClient();
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);

  const { data: runs, isLoading: runsLoading } = useQuery({
    queryKey: ["evaluation", "runs"],
    queryFn: () => evaluationApi.listRuns().then((r) => r.data),
    refetchInterval: 8000,
  });

  const { data: selectedRun } = useQuery({
    queryKey: ["evaluation", "run", selectedRunId],
    queryFn: () => evaluationApi.getRun(selectedRunId!).then((r) => r.data),
    enabled: !!selectedRunId,
  });

  async function triggerEval() {
    setTriggering(true);
    try {
      await evaluationApi.triggerRun("Dashboard-triggered evaluation");
      toast.success("Evaluation job queued. This may take a few minutes.");
      qc.invalidateQueries({ queryKey: ["evaluation"] });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to trigger evaluation.";
      toast.error(msg);
    } finally {
      setTriggering(false);
    }
  }

  // Build PR curve data for chart
  const prCurveData = selectedRun?.pr_curve_data
    ? selectedRun.pr_curve_data.precision.map((p, i) => ({
        recall: selectedRun.pr_curve_data!.recall[i].toFixed(3),
        precision: p.toFixed(3),
      }))
    : [];

  const rocCurveData = selectedRun?.roc_curve_data
    ? selectedRun.roc_curve_data.fpr.map((f, i) => ({
        fpr: f.toFixed(3),
        tpr: selectedRun.roc_curve_data!.tpr[i].toFixed(3),
      }))
    : [];

  return (
    <div className="p-6 space-y-5 max-w-6xl mx-auto">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <FlaskConical className="w-5 h-5 text-emerald-400" />
            Evaluation Lab
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Run model evaluations on stored transactions with ground-truth labels.
          </p>
        </div>
        {user?.role === "admin" && (
          <button
            id="trigger-eval"
            onClick={triggerEval}
            disabled={triggering}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm font-semibold transition-colors"
          >
            {triggering ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {triggering ? "Queuing…" : "Run Evaluation"}
          </button>
        )}
      </div>

      <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
        <p className="text-[11px] text-amber-400/80">
          Evaluation uses all stored transactions with ground-truth labels (Class column from CSV).
          Requires a trained and active model artifact. Only administrators can trigger evaluations.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Run list */}
        <div className="card-glass overflow-hidden">
          <div className="px-4 py-3 border-b border-border/40">
            <h2 className="text-sm font-semibold text-foreground">Evaluation Runs</h2>
          </div>
          <div className="divide-y divide-border/20 max-h-[500px] overflow-y-auto">
            {runsLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="px-4 py-3 space-y-1.5">
                  <div className="skeleton h-4 w-32" />
                  <div className="skeleton h-3 w-20" />
                </div>
              ))
            ) : !runs?.length ? (
              <p className="px-4 py-8 text-xs text-muted-foreground text-center">No evaluation runs yet.</p>
            ) : (
              runs.map((run) => (
                <button
                  key={run.id}
                  onClick={() => setSelectedRunId(run.id)}
                  className={`w-full text-left px-4 py-3 hover:bg-muted/30 transition-colors ${selectedRunId === run.id ? "bg-emerald-500/5 border-l-2 border-emerald-500" : ""}`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <StatusBadge status={run.status} />
                    <span className="text-[10px] text-muted-foreground">{formatDate(run.created_at)}</span>
                  </div>
                  <p className="text-xs text-muted-foreground truncate">{run.dataset_description ?? "Evaluation"}</p>
                  {run.pr_auc != null && (
                    <p className="text-xs text-emerald-400 font-semibold mt-0.5">PR-AUC: {formatPercent(run.pr_auc)}</p>
                  )}
                </button>
              ))
            )}
          </div>
        </div>

        {/* Run details */}
        <div className="lg:col-span-2 space-y-4">
          {!selectedRun ? (
            <div className="card-glass flex flex-col items-center justify-center h-64">
              <TrendingUp className="w-10 h-10 text-muted-foreground/30 mb-3" />
              <p className="text-sm text-muted-foreground">Select an evaluation run to view metrics and curves.</p>
            </div>
          ) : (
            <>
              {/* Metrics grid */}
              <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
                {[
                  { label: "Accuracy", value: selectedRun.accuracy },
                  { label: "Precision", value: selectedRun.precision },
                  { label: "Recall", value: selectedRun.recall },
                  { label: "F1 Score", value: selectedRun.f1_score },
                  { label: "Macro F1", value: selectedRun.macro_f1 },
                  { label: "PR-AUC", value: selectedRun.pr_auc },
                  { label: "ROC-AUC", value: selectedRun.roc_auc },
                  { label: "FP Rate", value: selectedRun.false_positive_rate },
                ].map(({ label, value }) => (
                  <motion.div
                    key={label}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="card-glass p-3"
                  >
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wide">{label}</p>
                    <p className="text-lg font-bold text-foreground mt-0.5">{value != null ? formatPercent(value) : "—"}</p>
                  </motion.div>
                ))}
                <div className="card-glass p-3">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Samples</p>
                  <p className="text-sm font-bold text-foreground mt-0.5">{selectedRun.num_samples ?? "—"}</p>
                  <p className="text-[10px] text-muted-foreground">
                    +{selectedRun.num_positive ?? 0} / −{selectedRun.num_negative ?? 0}
                  </p>
                </div>
              </div>

              {/* Confusion matrix */}
              {selectedRun.confusion_matrix && (
                <div className="card-glass p-4">
                  <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">Confusion Matrix</h3>
                  <div className="grid grid-cols-2 gap-2 max-w-xs">
                    {[
                      { label: "True Negative (TN)", val: selectedRun.confusion_matrix[0]?.[0], cls: "text-emerald-400" },
                      { label: "False Positive (FP)", val: selectedRun.confusion_matrix[0]?.[1], cls: "text-amber-400" },
                      { label: "False Negative (FN)", val: selectedRun.confusion_matrix[1]?.[0], cls: "text-amber-400" },
                      { label: "True Positive (TP)", val: selectedRun.confusion_matrix[1]?.[1], cls: "text-emerald-400" },
                    ].map(({ label, val, cls }) => (
                      <div key={label} className="p-3 rounded-lg bg-muted/30 text-center">
                        <p className="text-[10px] text-muted-foreground">{label}</p>
                        <p className={`text-xl font-bold ${cls}`}>{val ?? "—"}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* PR curve */}
              {prCurveData.length > 0 && (
                <div className="card-glass p-5">
                  <h3 className="text-sm font-semibold text-foreground mb-3">Precision-Recall Curve</h3>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={prCurveData} margin={{ left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 35% 17%)" />
                      <XAxis dataKey="recall" tick={{ fontSize: 10, fill: "hsl(215 20% 55%)" }} label={{ value: "Recall", position: "insideBottom", offset: -2, fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 10, fill: "hsl(215 20% 55%)" }} label={{ value: "Precision", angle: -90, position: "insideLeft", fontSize: 10 }} />
                      <Tooltip contentStyle={{ background: "hsl(222 44% 10%)", border: "1px solid hsl(222 35% 17%)", borderRadius: 8, fontSize: 11 }} />
                      <Line type="monotone" dataKey="precision" stroke="#10b981" dot={false} strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* ROC curve */}
              {rocCurveData.length > 0 && (
                <div className="card-glass p-5">
                  <h3 className="text-sm font-semibold text-foreground mb-3">ROC Curve</h3>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={rocCurveData} margin={{ left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 35% 17%)" />
                      <XAxis dataKey="fpr" tick={{ fontSize: 10, fill: "hsl(215 20% 55%)" }} label={{ value: "FPR", position: "insideBottom", offset: -2, fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 10, fill: "hsl(215 20% 55%)" }} label={{ value: "TPR", angle: -90, position: "insideLeft", fontSize: 10 }} />
                      <Tooltip contentStyle={{ background: "hsl(222 44% 10%)", border: "1px solid hsl(222 35% 17%)", borderRadius: 8, fontSize: 11 }} />
                      <Line type="monotone" dataKey="tpr" stroke="#3b82f6" dot={false} strokeWidth={2} name="ROC" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
