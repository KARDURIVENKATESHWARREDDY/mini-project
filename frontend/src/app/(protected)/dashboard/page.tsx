"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api";
import { KpiCard } from "@/components/ui/kpi-card";
import { RiskBadge } from "@/components/ui/badges";
import {
  formatNumber, formatCurrency, formatPercent, formatRelativeTime,
} from "@/lib/utils";
import {
  Activity, AlertTriangle, ShieldCheck, Clock, Search,
  TrendingUp, Cpu, CheckCircle2, XCircle, Minus,
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";
import { motion } from "framer-motion";

export default function DashboardPage() {
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: () => dashboardApi.summary().then((r) => r.data),
  });
  const { data: volumeTrend } = useQuery({
    queryKey: ["dashboard", "volumeTrend"],
    queryFn: () => dashboardApi.volumeTrend(30).then((r) => r.data),
  });
  const { data: fraudTrend } = useQuery({
    queryKey: ["dashboard", "fraudTrend"],
    queryFn: () => dashboardApi.fraudTrend(30).then((r) => r.data),
  });
  const { data: riskDist } = useQuery({
    queryKey: ["dashboard", "riskDist"],
    queryFn: () => dashboardApi.riskDistribution().then((r) => r.data),
  });
  const { data: recentAlerts } = useQuery({
    queryKey: ["dashboard", "recentAlerts"],
    queryFn: () => dashboardApi.recentAlerts(8).then((r) => r.data),
  });
  const { data: modelHealth } = useQuery({
    queryKey: ["dashboard", "modelHealth"],
    queryFn: () => dashboardApi.modelHealth().then((r) => r.data),
  });

  const riskDistData = riskDist
    ? [
        { name: "Low", value: riskDist.low, color: "#10b981" },
        { name: "Medium", value: riskDist.medium, color: "#f59e0b" },
        { name: "High", value: riskDist.high, color: "#ef4444" },
      ]
    : [];

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-foreground">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Real-time fraud risk intelligence overview
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        <KpiCard
          title="Total Transactions"
          value={formatNumber(summary?.total_transactions)}
          icon={<Activity className="w-4 h-4" />}
          loading={summaryLoading}
        />
        <KpiCard
          title="High-Risk Alerts"
          value={formatNumber(summary?.high_risk_count)}
          icon={<AlertTriangle className="w-4 h-4" />}
          variant="danger"
          loading={summaryLoading}
        />
        <KpiCard
          title="Confirmed Fraud"
          value={formatNumber(summary?.confirmed_fraud_count)}
          icon={<ShieldCheck className="w-4 h-4" />}
          variant="danger"
          loading={summaryLoading}
        />
        <KpiCard
          title="Pending Review"
          value={formatNumber(summary?.pending_review_count)}
          icon={<Clock className="w-4 h-4" />}
          variant="warning"
          loading={summaryLoading}
        />
        <KpiCard
          title="Open Investigations"
          value={formatNumber(summary?.open_investigations)}
          icon={<Search className="w-4 h-4" />}
          variant="warning"
          loading={summaryLoading}
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Volume trend */}
        <div className="lg:col-span-2 card-glass p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            Transaction Volume (30 days)
          </h2>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={volumeTrend ?? []} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="volGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "hsl(215 20% 55%)" }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(215 20% 55%)" }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{
                  background: "hsl(222 44% 10%)",
                  border: "1px solid hsl(222 35% 17%)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelStyle={{ color: "hsl(210 40% 96%)" }}
                itemStyle={{ color: "#10b981" }}
              />
              <Area type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2} fill="url(#volGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Risk distribution */}
        <div className="card-glass p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">Risk Distribution</h2>
          <div className="flex flex-col items-center">
            <ResponsiveContainer width="100%" height={150}>
              <PieChart>
                <Pie
                  data={riskDistData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={65}
                  strokeWidth={0}
                >
                  {riskDistData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "hsl(222 44% 10%)",
                    border: "1px solid hsl(222 35% 17%)",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex gap-4 mt-2">
              {riskDistData.map((d) => (
                <div key={d.name} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span className="w-2 h-2 rounded-full" style={{ background: d.color }} />
                  {d.name}: <span className="font-medium text-foreground">{formatNumber(d.value)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Fraud trend */}
        <div className="card-glass p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            High-Risk Trend (30 days)
          </h2>
          <ResponsiveContainer width="100%" height={150}>
            <BarChart data={fraudTrend ?? []} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <XAxis dataKey="date" tick={{ fontSize: 9, fill: "hsl(215 20% 55%)" }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 9, fill: "hsl(215 20% 55%)" }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{
                  background: "hsl(222 44% 10%)",
                  border: "1px solid hsl(222 35% 17%)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                itemStyle={{ color: "#ef4444" }}
              />
              <Bar dataKey="value" fill="#ef4444" radius={[3, 3, 0, 0]} opacity={0.8} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Recent alerts */}
        <div className="lg:col-span-2 card-glass p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">Recent High-Risk Alerts</h2>
          <div className="space-y-2 overflow-auto max-h-[200px]">
            {!recentAlerts || recentAlerts.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-8">No high-risk alerts yet.</p>
            ) : (
              recentAlerts.map((alert) => (
                <motion.div
                  key={alert.prediction_id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center gap-3 p-2.5 rounded-lg bg-muted/40 hover:bg-muted/60 transition-colors text-xs"
                >
                  <RiskBadge risk={alert.risk_category} showIcon={false} />
                  <span className="text-muted-foreground font-mono truncate flex-1">
                    {alert.transaction_id.slice(0, 8)}…
                  </span>
                  <span className="font-medium text-foreground">{formatCurrency(alert.amount)}</span>
                  <span className="text-red-400 font-semibold">{formatPercent(alert.fraud_probability)}</span>
                  <span className="text-muted-foreground">{formatRelativeTime(alert.predicted_at)}</span>
                </motion.div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Model status + metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Model health */}
        <div className="card-glass p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-emerald-400" />
            Channel Availability
          </h2>
          {modelHealth ? (
            <div className="space-y-2">
              {[
                { label: "TAB-Net (Tabular)", ok: modelHealth.tab_net_available },
                { label: "SEQ-Net (Sequential)", ok: modelHealth.seq_net_available },
                { label: "GEO-Net (Geographic)", ok: modelHealth.geo_net_available },
                { label: "PROF-Net (Profile)", ok: modelHealth.prof_net_available },
                { label: "CFRI Fusion", ok: modelHealth.fusion_available },
              ].map(({ label, ok }) => (
                <div key={label} className="flex items-center gap-2 text-xs">
                  {ok ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                  )}
                  <span className={ok ? "text-foreground" : "text-muted-foreground"}>{label}</span>
                  <span className={`ml-auto text-[10px] font-medium ${ok ? "text-emerald-400" : "text-muted-foreground"}`}>
                    {ok ? "Online" : "Unavailable"}
                  </span>
                </div>
              ))}
              {modelHealth.notes && (
                <p className="text-[10px] text-muted-foreground mt-2 leading-relaxed border-t border-border/40 pt-2">
                  {modelHealth.notes}
                </p>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => <div key={i} className="skeleton h-5 rounded" />)}
            </div>
          )}
        </div>

        {/* Latest metrics */}
        <div className="card-glass p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">
            Latest Evaluation Metrics
            {summary?.active_model && (
              <span className="ml-2 text-[10px] text-muted-foreground font-normal">
                {summary.active_model.name} v{summary.active_model.version_tag}
              </span>
            )}
          </h2>
          {summary?.latest_metrics ? (
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: "Precision", value: summary.latest_metrics.precision },
                { label: "Recall", value: summary.latest_metrics.recall },
                { label: "F1 Score", value: summary.latest_metrics.f1_score },
                { label: "PR-AUC", value: summary.latest_metrics.pr_auc },
                { label: "ROC-AUC", value: summary.latest_metrics.roc_auc },
              ].map(({ label, value }) => (
                <div key={label} className="p-2.5 rounded-lg bg-muted/40">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wide">{label}</p>
                  <p className="text-lg font-bold text-emerald-400 mt-0.5">{formatPercent(value)}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-32 text-center">
              <Minus className="w-8 h-8 text-muted-foreground/30 mb-2" />
              <p className="text-xs text-muted-foreground">
                {summary?.active_model ? "No evaluation runs completed yet." : "No active model registered."}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
