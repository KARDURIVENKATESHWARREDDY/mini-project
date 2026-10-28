"use client";

import { useState, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { batchApi } from "@/lib/api";
import { StatusBadge } from "@/components/ui/badges";
import { formatDate, formatNumber } from "@/lib/utils";
import { Upload, FileText, AlertTriangle, RefreshCw, ChevronLeft, ChevronRight, CheckCircle2 } from "lucide-react";
import { motion } from "framer-motion";
import { toast } from "sonner";

export default function BatchPage() {
  const [page, setPage] = useState(1);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const qc = useQueryClient();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["batch", "jobs", page],
    queryFn: () => batchApi.listJobs(page).then((r) => r.data),
    refetchInterval: 5000,
  });

  async function uploadFile(file: File) {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      toast.error("Only CSV files are accepted.");
      return;
    }
    setUploading(true);
    try {
      await batchApi.upload(file);
      toast.success("Batch job submitted. Processing will start shortly.");
      qc.invalidateQueries({ queryKey: ["batch"] });
      setPage(1);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Upload failed.";
      toast.error(msg);
    } finally {
      setUploading(false);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) uploadFile(file);
    e.target.value = "";
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) uploadFile(file);
  }

  const totalPages = data ? Math.ceil(data.total / 20) : 1;

  return (
    <div className="p-6 space-y-5 max-w-5xl mx-auto">
      <div>
        <h1 className="text-xl font-bold text-foreground">Batch Screening</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Upload a CSV file to score multiple transactions in one batch.
        </p>
      </div>

      {/* Upload zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
        className={`card-glass p-10 flex flex-col items-center gap-3 cursor-pointer transition-all duration-200 ${
          dragOver ? "border-emerald-500/60 bg-emerald-500/5" : "hover:border-border hover:bg-muted/20"
        } ${uploading ? "opacity-60 cursor-not-allowed" : ""}`}
      >
        <input ref={fileInputRef} type="file" accept=".csv" className="hidden" onChange={handleFileChange} id="batch-file-input" />
        <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${dragOver ? "bg-emerald-500/20" : "bg-muted"}`}>
          {uploading ? (
            <RefreshCw className="w-6 h-6 text-emerald-400 animate-spin" />
          ) : (
            <Upload className={`w-6 h-6 ${dragOver ? "text-emerald-400" : "text-muted-foreground"}`} />
          )}
        </div>
        <div className="text-center">
          <p className="text-sm font-medium text-foreground">
            {uploading ? "Uploading…" : dragOver ? "Drop CSV here" : "Drop a CSV file or click to browse"}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Must include: Time, V1–V28, Amount columns. Max 50 MB.
          </p>
        </div>
      </div>

      {/* Format reminder */}
      <div className="flex items-start gap-2 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
        <FileText className="w-3.5 h-3.5 text-blue-400 shrink-0 mt-0.5" />
        <div className="text-[11px] text-blue-400/80 space-y-1">
          <p className="font-medium">Expected CSV format (ULB/Kaggle creditcard.csv schema)</p>
          <p>Required columns: Time, V1, V2, …, V28, Amount. Optional: Class (ground-truth label).</p>
        </div>
      </div>

      {/* Jobs table */}
      <div className="card-glass overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-border/40">
          <h2 className="text-sm font-semibold text-foreground">Batch Jobs</h2>
          <button
            id="batch-refresh"
            onClick={() => refetch()}
            className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            Refresh
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/30 bg-muted/20">
                {["Filename", "Status", "Processed", "Rejected", "Total", "Submitted", "Completed", "Error"].map((h) => (
                  <th key={h} className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="border-b border-border/20">
                      {Array.from({ length: 8 }).map((_, j) => (
                        <td key={j} className="px-4 py-3"><div className="skeleton h-4 w-20" /></td>
                      ))}
                    </tr>
                  ))
                : !data?.items.length
                ? (
                    <tr>
                      <td colSpan={8} className="px-4 py-10 text-center text-sm text-muted-foreground">
                        No batch jobs yet. Upload a CSV to get started.
                      </td>
                    </tr>
                  )
                : data.items.map((job) => (
                    <motion.tr
                      key={job.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="border-b border-border/20 hover:bg-muted/20 transition-colors"
                    >
                      <td className="px-4 py-3 text-xs text-foreground font-medium max-w-[200px] truncate">{job.filename}</td>
                      <td className="px-4 py-3"><StatusBadge status={job.status} /></td>
                      <td className="px-4 py-3 text-xs text-emerald-400 font-medium">{formatNumber(job.processed_rows)}</td>
                      <td className="px-4 py-3 text-xs text-red-400">{formatNumber(job.rejected_rows)}</td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">{job.total_rows != null ? formatNumber(job.total_rows) : "—"}</td>
                      <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">{formatDate(job.created_at)}</td>
                      <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">{job.completed_at ? formatDate(job.completed_at) : "—"}</td>
                      <td className="px-4 py-3 text-xs text-red-400 max-w-[150px] truncate">{job.error_message ?? "—"}</td>
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

      {/* Note */}
      <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
        <p className="text-[11px] text-amber-400/80">
          Batch jobs run asynchronously. The table auto-refreshes every 5 seconds.
          Large files may take several minutes to process.
        </p>
      </div>
    </div>
  );
}
