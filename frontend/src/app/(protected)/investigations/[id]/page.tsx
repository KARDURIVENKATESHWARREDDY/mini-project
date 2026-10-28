"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { investigationsApi } from "@/lib/api";
import { StatusBadge } from "@/components/ui/badges";
import { formatDate, formatCurrency } from "@/lib/utils";
import { ArrowLeft, MessageSquare, AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { useAuthStore } from "@/store/auth";

const EVENT_TYPES = [
  { value: "note", label: "Add Note" },
  { value: "escalate", label: "Escalate" },
  { value: "resolve_fraud", label: "Resolve as Fraud" },
  { value: "resolve_legitimate", label: "Resolve as Legitimate" },
  { value: "dismiss", label: "Dismiss" },
];

export default function InvestigationDetailPage() {
  const { user } = useAuthStore();
  const rawParams = useParams();
  const id = (rawParams?.id as string) ?? "";
  const qc = useQueryClient();
  const [eventType, setEventType] = useState("note");
  const [notes, setNotes] = useState("");
  const [confirmedLabel, setConfirmedLabel] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);

  const { data: inv, isLoading } = useQuery({
    queryKey: ["investigation", id],
    queryFn: () => investigationsApi.get(id).then((r) => r.data),
    enabled: !!id,
  });

  async function addEvent(e: React.FormEvent) {
    e.preventDefault();
    if (!notes.trim() && eventType === "note") {
      toast.error("Please enter a note.");
      return;
    }
    setSubmitting(true);
    try {
      await investigationsApi.addEvent(
        id,
        eventType,
        notes || undefined,
        confirmedLabel !== "" ? parseInt(confirmedLabel) : undefined,
      );
      toast.success("Event recorded.");
      setNotes("");
      setConfirmedLabel("");
      qc.invalidateQueries({ queryKey: ["investigation", id] });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to record event.";
      toast.error(msg);
    } finally {
      setSubmitting(false);
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

  if (!inv) {
    return (
      <div className="p-6 text-center">
        <p className="text-muted-foreground">Investigation not found.</p>
        <Link href="/investigations" className="text-emerald-400 text-sm mt-2 inline-block hover:underline">← Back</Link>
      </div>
    );
  }

  const isResolved = ["resolved", "closed"].includes((inv as { status: string }).status);

  return (
    <div className="p-6 space-y-5 max-w-4xl mx-auto">
      <div className="flex items-center gap-3">
        <Link href="/investigations" className="text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <h1 className="text-xl font-bold text-foreground">Investigation</h1>
          <p className="text-xs text-muted-foreground font-mono">{id}</p>
        </div>
      </div>

      {/* Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card-glass p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Status</p>
          <StatusBadge status={(inv as { status: string }).status} />
        </div>
        <div className="card-glass p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Priority</p>
          <p className="text-sm font-semibold capitalize text-foreground">{(inv as { priority: string }).priority}</p>
        </div>
        <div className="card-glass p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Amount</p>
          <p className="text-sm font-semibold text-foreground">
            {(inv as { transaction?: { amount?: number } }).transaction?.amount != null
              ? formatCurrency((inv as { transaction: { amount: number } }).transaction.amount)
              : "—"}
          </p>
        </div>
        <div className="card-glass p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Confirmed Label</p>
          <p className={`text-sm font-semibold ${(inv as { confirmed_label?: number }).confirmed_label === 1 ? "text-red-400" : (inv as { confirmed_label?: number }).confirmed_label === 0 ? "text-emerald-400" : "text-muted-foreground"}`}>
            {(inv as { confirmed_label?: number }).confirmed_label === 1 ? "Fraud"
              : (inv as { confirmed_label?: number }).confirmed_label === 0 ? "Legitimate"
              : "Unresolved"}
          </p>
        </div>
      </div>

      {/* Meta */}
      <div className="card-glass p-4 text-xs space-y-1.5 text-muted-foreground">
        <p>Opened by: <span className="text-foreground font-medium">{(inv as { opened_by?: string }).opened_by ?? "—"}</span></p>
        <p>Assigned to: <span className="text-foreground font-medium">{(inv as { assigned_to?: string }).assigned_to ?? "Unassigned"}</span></p>
        <p>Opened: {formatDate((inv as { opened_at: string }).opened_at)}</p>
        {(inv as { resolved_at?: string }).resolved_at && <p>Resolved: {formatDate((inv as { resolved_at: string }).resolved_at)}</p>}
        {(inv as { resolution_notes?: string }).resolution_notes && (
          <p>Resolution notes: <span className="text-foreground">{(inv as { resolution_notes: string }).resolution_notes}</span></p>
        )}
        <p>
          Transaction: <Link href={`/transactions/${(inv as { transaction_id: string }).transaction_id}`} className="text-emerald-400 hover:underline font-mono">
            {(inv as { transaction_id: string }).transaction_id.slice(0, 16)}…
          </Link>
        </p>
      </div>

      {/* Timeline */}
      <div className="card-glass p-5">
        <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-emerald-400" />
          Event Timeline
        </h2>
        <div className="space-y-3">
          {((inv as { events?: Array<{ id: string; event_type: string; actor?: string; notes?: string; created_at: string }> }).events ?? []).map((ev) => (
            <div key={ev.id} className="flex gap-3">
              <div className="flex flex-col items-center">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 border ${
                  ev.event_type.includes("resolve_fraud") || ev.event_type === "escalate" ? "bg-red-500/10 border-red-500/30"
                  : ev.event_type.includes("legitimate") ? "bg-emerald-500/10 border-emerald-500/30"
                  : "bg-muted border-border/50"
                }`}>
                  {ev.event_type.includes("resolve_fraud") ? <AlertTriangle className="w-3 h-3 text-red-400" />
                  : ev.event_type.includes("legitimate") ? <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  : ev.event_type === "dismiss" ? <XCircle className="w-3 h-3 text-muted-foreground" />
                  : <MessageSquare className="w-3 h-3 text-muted-foreground" />}
                </div>
                <div className="w-px flex-1 bg-border/30 mt-1" />
              </div>
              <div className="pb-4 flex-1">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xs font-medium text-foreground capitalize">{ev.event_type.replace("_", " ")}</span>
                  <span className="text-[10px] text-muted-foreground">by {ev.actor ?? "System"}</span>
                  <span className="text-[10px] text-muted-foreground ml-auto">{formatDate(ev.created_at)}</span>
                </div>
                {ev.notes && <p className="text-xs text-muted-foreground">{ev.notes}</p>}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Add event form */}
      {(user?.role === "analyst" || user?.role === "admin") && !isResolved && (
        <div className="card-glass p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">Record Action</h2>
          <form onSubmit={addEvent} className="space-y-3">
            <div className="flex gap-3">
              <select
                id="event-type-select"
                value={eventType}
                onChange={(e) => setEventType(e.target.value)}
                className="flex-1 py-2 px-3 text-sm bg-muted/50 border border-border/50 rounded-lg text-foreground focus:outline-none focus:border-emerald-500/50 transition-colors"
              >
                {EVENT_TYPES.map((et) => (
                  <option key={et.value} value={et.value}>{et.label}</option>
                ))}
              </select>
              {(eventType === "resolve_fraud" || eventType === "resolve_legitimate") && (
                <select
                  value={confirmedLabel}
                  onChange={(e) => setConfirmedLabel(e.target.value)}
                  className="py-2 px-3 text-sm bg-muted/50 border border-border/50 rounded-lg text-foreground focus:outline-none focus:border-emerald-500/50 transition-colors"
                >
                  <option value="">Label (opt.)</option>
                  <option value="1">Fraud (1)</option>
                  <option value="0">Legitimate (0)</option>
                </select>
              )}
            </div>
            <textarea
              id="event-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Notes (optional for some actions)…"
              rows={3}
              className="w-full px-3 py-2 text-sm bg-muted/50 border border-border/50 rounded-lg text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-emerald-500/50 transition-colors resize-none"
            />
            <button
              id="add-event-submit"
              type="submit"
              disabled={submitting}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm font-semibold transition-colors"
            >
              {submitting ? "Submitting…" : "Record Action"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
