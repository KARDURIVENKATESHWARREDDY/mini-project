"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { modelsApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Database, CheckCircle2, XCircle, Cpu, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { useAuthStore } from "@/store/auth";
import { motion } from "framer-motion";

export default function ModelsPage() {
  const { user } = useAuthStore();
  const qc = useQueryClient();

  const { data: models, isLoading } = useQuery({
    queryKey: ["models"],
    queryFn: () => modelsApi.list().then((r) => r.data),
  });

  async function activateModel(id: string, name: string) {
    try {
      await modelsApi.activate(id);
      toast.success(`Model "${name}" is now active.`);
      qc.invalidateQueries({ queryKey: ["models"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Activation failed.";
      toast.error(msg);
    }
  }

  const channelColors: Record<string, string> = {
    tab_net: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
    seq_net: "text-blue-400 bg-blue-500/10 border-blue-500/30",
    geo_net: "text-violet-400 bg-violet-500/10 border-violet-500/30",
    prof_net: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  };

  return (
    <div className="p-6 space-y-5 max-w-5xl mx-auto">
      <div>
        <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
          <Database className="w-5 h-5 text-emerald-400" />
          Model Registry
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Manage and activate trained model versions.
        </p>
      </div>

      <div className="space-y-3">
        {isLoading
          ? Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="card-glass p-5 space-y-3">
                <div className="skeleton h-5 w-48" />
                <div className="skeleton h-4 w-64" />
              </div>
            ))
          : !models?.length
          ? (
              <div className="card-glass p-10 text-center">
                <Cpu className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">No models registered yet.</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Train a model using <code className="bg-muted px-1 rounded">ml/train_tabnet.py</code> and register it via the API.
                </p>
              </div>
            )
          : models.map((mv) => (
              <motion.div
                key={mv.id}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                className={`card-glass p-5 flex items-start gap-5 ${mv.is_active ? "border-emerald-500/30" : ""}`}
              >
                <div className="flex-1 min-w-0 space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-sm font-bold text-foreground">{mv.name}</h2>
                    <span className="text-xs font-mono text-muted-foreground">v{mv.version_tag}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border uppercase font-medium tracking-wide ${channelColors[mv.channel] ?? "text-muted-foreground bg-muted"}`}>
                      {mv.channel.replace("_", "-")}
                    </span>
                    {mv.is_active && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-semibold">
                        ACTIVE
                      </span>
                    )}
                    {mv.is_experimental && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/25 font-medium">
                        Experimental
                      </span>
                    )}
                  </div>
                  {mv.description && (
                    <p className="text-xs text-muted-foreground">{mv.description}</p>
                  )}
                  <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
                    <span>Registered: {formatDate(mv.registered_at)}</span>
                    {mv.artifact_path && (
                      <span className="font-mono truncate max-w-xs">{mv.artifact_path}</span>
                    )}
                  </div>
                  {mv.hyperparameters && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {Object.entries(mv.hyperparameters).slice(0, 6).map(([k, v]) => (
                        <span key={k} className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-mono">
                          {k}={String(v)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                {user?.role === "admin" && !mv.is_active && (
                  <button
                    id={`activate-${mv.id}`}
                    onClick={() => activateModel(mv.id, mv.name)}
                    className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 text-xs bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors font-medium"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Activate
                  </button>
                )}
                {mv.is_active && (
                  <div className="shrink-0 flex items-center gap-1.5 text-xs text-emerald-400">
                    <CheckCircle2 className="w-4 h-4" />
                    Active
                  </div>
                )}
              </motion.div>
            ))}
      </div>
    </div>
  );
}
