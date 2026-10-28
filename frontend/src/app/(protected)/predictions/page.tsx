"use client";

import { useState } from "react";
import { predictionsApi } from "@/lib/api";
import { RiskBadge } from "@/components/ui/badges";
import { formatPercent, formatDate } from "@/lib/utils";
import { Shield, AlertTriangle, Send, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import type { PredictionResult } from "@/lib/api";

const FEATURE_NAMES = [
  "Time", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9",
  "V10", "V11", "V12", "V13", "V14", "V15", "V16", "V17", "V18",
  "V19", "V20", "V21", "V22", "V23", "V24", "V25", "V26", "V27", "V28", "Amount",
];

const SAMPLE_FRAUD = {
  Time: 406.0, V1: -2.312, V2: 1.952, V3: -1.610, V4: 3.998, V5: -0.522,
  V6: -1.427, V7: -2.538, V8: 1.392, V9: -2.770, V10: -2.773, V11: 3.202,
  V12: -2.900, V13: -0.595, V14: -4.289, V15: 0.390, V16: -1.141, V17: -2.831,
  V18: -0.017, V19: 0.417, V20: 0.127, V21: 0.517, V22: -0.035, V23: -0.466,
  V24: 0.320, V25: 0.044, V26: -0.202, V27: 0.473, V28: 0.260, Amount: 239.93,
};

export default function PredictionsPage() {
  const [features, setFeatures] = useState<Record<string, string>>(
    Object.fromEntries(FEATURE_NAMES.map((f) => [f, ""]))
  );
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PredictionResult | null>(null);

  function fillSample() {
    setFeatures(Object.fromEntries(Object.entries(SAMPLE_FRAUD).map(([k, v]) => [k, String(v)])));
    setResult(null);
  }

  function clearForm() {
    setFeatures(Object.fromEntries(FEATURE_NAMES.map((f) => [f, ""])));
    setResult(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const parsed: Record<string, number> = {};
    for (const f of FEATURE_NAMES) {
      const v = parseFloat(features[f]);
      if (isNaN(v)) {
        toast.error(`Invalid value for feature "${f}". Please enter a number.`);
        return;
      }
      parsed[f] = v;
    }
    setLoading(true);
    try {
      const res = await predictionsApi.single({ features: parsed });
      setResult(res.data);
      toast.success("Prediction completed.");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Prediction failed.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 space-y-5 max-w-4xl mx-auto">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <Shield className="w-5 h-5 text-emerald-400" />
            Single Transaction Prediction
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Score a transaction feature vector against the active TAB-Net model.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fillSample}
            className="text-xs px-3 py-1.5 rounded-lg bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground transition-colors border border-border/50"
          >
            Fill Sample (Fraud)
          </button>
          <button
            onClick={clearForm}
            className="text-xs px-3 py-1.5 rounded-lg bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground transition-colors border border-border/50"
          >
            <RefreshCw className="w-3 h-3 inline mr-1" />
            Clear
          </button>
        </div>
      </div>

      {/* Warning */}
      <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
        <p className="text-[11px] text-amber-400/80 leading-snug">
          Thresholds (low=0.3, high=0.7) are configurable defaults and have not been validated on production data.
          This is a research prototype — do not use predictions to automatically block transactions.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Features grid */}
        <div className="card-glass p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">Feature Vector (Time, V1–V28, Amount)</h2>
          <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
            {FEATURE_NAMES.map((feat) => (
              <div key={feat}>
                <label className="block text-[10px] text-muted-foreground uppercase tracking-wide mb-1">{feat}</label>
                <input
                  type="number"
                  step="any"
                  id={`feat-${feat}`}
                  value={features[feat]}
                  onChange={(e) => setFeatures((f) => ({ ...f, [feat]: e.target.value }))}
                  placeholder="0.0"
                  className="w-full px-2.5 py-1.5 text-xs bg-muted/50 border border-border/50 rounded-lg text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-emerald-500/50 transition-colors font-mono"
                />
              </div>
            ))}
          </div>
        </div>

        <button
          id="predict-submit"
          type="submit"
          disabled={loading}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold text-sm transition-colors"
        >
          {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          {loading ? "Scoring…" : "Run Prediction"}
        </button>
      </form>

      {/* Result */}
      {result && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="card-glass p-6 border border-border/80"
          style={{ borderColor: result.risk_category === "high" ? "rgba(239,68,68,0.4)" : result.risk_category === "medium" ? "rgba(245,158,11,0.4)" : "rgba(16,185,129,0.4)" }}
        >
          <h2 className="text-sm font-semibold text-foreground mb-4">Prediction Result</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Risk Level</p>
              <RiskBadge risk={result.risk_category} />
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Fraud Probability</p>
              <p className={`text-2xl font-bold ${result.risk_category === "high" ? "text-red-400" : result.risk_category === "medium" ? "text-amber-400" : "text-emerald-400"}`}>
                {formatPercent(result.fraud_probability)}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Model</p>
              <p className="text-sm text-foreground font-medium">{result.model_name}</p>
              <p className="text-xs text-muted-foreground">v{result.model_version}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Scored At</p>
              <p className="text-xs text-foreground">{formatDate(result.predicted_at)}</p>
            </div>
          </div>

          {/* Probability bar */}
          <div className="mb-4">
            <div className="flex justify-between text-[10px] text-muted-foreground mb-1">
              <span>0%</span>
              <span>Threshold Low (30%)</span>
              <span>Threshold High (70%)</span>
              <span>100%</span>
            </div>
            <div className="h-3 bg-muted/50 rounded-full relative overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${result.fraud_probability * 100}%`,
                  background: result.risk_category === "high" ? "#ef4444" : result.risk_category === "medium" ? "#f59e0b" : "#10b981",
                }}
              />
              <div className="absolute top-0 left-[30%] h-full w-px bg-border" />
              <div className="absolute top-0 left-[70%] h-full w-px bg-border" />
            </div>
          </div>

          {/* SHAP values if available */}
          {result.shap_values && (
            <div>
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                Top Feature Attributions (SHAP)
              </h3>
              <div className="space-y-1">
                {Object.entries(result.shap_values)
                  .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
                  .slice(0, 10)
                  .map(([feat, val]) => {
                    const maxAbsVal = Math.max(...Object.values(result.shap_values!).map(Math.abs));
                    const pct = maxAbsVal ? (Math.abs(val) / maxAbsVal) * 100 : 0;
                    return (
                      <div key={feat} className="flex items-center gap-2 text-xs">
                        <span className="w-10 text-muted-foreground font-mono text-right shrink-0">{feat}</span>
                        <div className="flex-1 h-3.5 bg-muted/30 rounded overflow-hidden">
                          <div
                            className="h-full rounded"
                            style={{ width: `${pct}%`, background: val > 0 ? "#ef4444" : "#10b981", opacity: 0.75 }}
                          />
                        </div>
                        <span className={`w-14 text-right font-mono shrink-0 ${val > 0 ? "text-red-400" : "text-emerald-400"}`}>
                          {val > 0 ? "+" : ""}{val.toFixed(4)}
                        </span>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {result.warnings.length > 0 && (
            <div className="mt-4 pt-4 border-t border-border/30">
              {result.warnings.map((w, i) => (
                <p key={i} className="text-[10px] text-muted-foreground flex items-start gap-1.5">
                  <AlertTriangle className="w-3 h-3 text-amber-400 shrink-0 mt-0.5" />
                  {w}
                </p>
              ))}
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
