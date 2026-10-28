"use client";

import { useAuthStore } from "@/store/auth";
import { healthApi } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { Settings, User, Shield, Activity, AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { formatDate } from "@/lib/utils";

export default function SettingsPage() {
  const { user, logout } = useAuthStore();

  const { data: health } = useQuery({
    queryKey: ["health", "ready"],
    queryFn: () => healthApi.readiness().then((r) => r.data),
    refetchInterval: 30_000,
  });

  return (
    <div className="p-6 space-y-5 max-w-3xl mx-auto">
      <div>
        <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
          <Settings className="w-5 h-5 text-emerald-400" />
          Settings
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">Account information and system status.</p>
      </div>

      {/* Profile */}
      <div className="card-glass p-6">
        <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <User className="w-4 h-4 text-emerald-400" />
          Profile
        </h2>
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-xl font-bold text-emerald-400">
            {user?.full_name?.charAt(0).toUpperCase() ?? "U"}
          </div>
          <div>
            <p className="text-base font-bold text-foreground">{user?.full_name}</p>
            <p className="text-sm text-muted-foreground">{user?.email}</p>
            <span className={`inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded border uppercase font-semibold tracking-wide ${
              user?.role === "admin" ? "text-red-400 bg-red-500/10 border-red-500/30"
              : user?.role === "analyst" ? "text-violet-400 bg-violet-500/10 border-violet-500/30"
              : "text-muted-foreground bg-muted border-border"
            }`}>
              {user?.role}
            </span>
          </div>
        </div>
        {user?.last_login_at && (
          <p className="text-xs text-muted-foreground mt-4">
            Last login: {formatDate(user.last_login_at)}
          </p>
        )}
      </div>

      {/* System status */}
      <div className="card-glass p-6">
        <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <Activity className="w-4 h-4 text-emerald-400" />
          System Status
        </h2>
        {health ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span className="text-foreground">API</span>
              <span className="ml-auto text-xs text-emerald-400 font-medium">Online</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              {health.checks?.database === "ok"
                ? <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                : <XCircle className="w-4 h-4 text-red-400" />}
              <span className="text-foreground">Database</span>
              <span className={`ml-auto text-xs font-medium ${health.checks?.database === "ok" ? "text-emerald-400" : "text-red-400"}`}>
                {health.checks?.database === "ok" ? "Connected" : health.checks?.database}
              </span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              {health.checks?.model === "loaded"
                ? <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                : <XCircle className="w-4 h-4 text-amber-400" />}
              <span className="text-foreground">ML Model</span>
              <span className={`ml-auto text-xs font-medium ${health.checks?.model === "loaded" ? "text-emerald-400" : "text-amber-400"}`}>
                {health.checks?.model === "loaded" ? "Loaded" : "Not Loaded"}
              </span>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => <div key={i} className="skeleton h-5 rounded" />)}
          </div>
        )}
      </div>

      {/* Research notice */}
      <div className="card-glass p-5 border-amber-500/20">
        <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          <Shield className="w-4 h-4 text-amber-400" />
          Research Prototype Disclaimer
        </h2>
        <div className="space-y-2 text-xs text-muted-foreground">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
            <p>CARD-Net is a research prototype developed at Anurag University, Department of Artificial Intelligence.</p>
          </div>
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
            <p>Model predictions are decision-support information only. Do not use them to automatically block or authorise transactions.</p>
          </div>
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
            <p>Fraud thresholds (low=0.3, high=0.7) are configurable defaults and have not been validated on production data.</p>
          </div>
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
            <p>The system uses the ULB/Kaggle creditcard benchmark dataset. Evaluation metrics apply to this dataset only.</p>
          </div>
        </div>
      </div>

      {/* Sign out */}
      <div className="card-glass p-5">
        <h2 className="text-sm font-semibold text-foreground mb-3">Session</h2>
        <button
          id="settings-logout"
          onClick={logout}
          className="px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 text-sm font-medium transition-colors"
        >
          Sign out
        </button>
      </div>
    </div>
  );
}
