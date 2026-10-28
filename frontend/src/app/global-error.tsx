"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[CARD-Net] Unhandled error:", error);
  }, [error]);

  return (
    <html lang="en">
      <body className="min-h-screen bg-[hsl(222,47%,7%)] flex items-center justify-center p-6">
        <div className="max-w-md w-full rounded-xl border border-red-500/30 bg-[hsl(222,44%,10%)] p-8 shadow-2xl">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <h1 className="text-base font-bold text-white">Something went wrong</h1>
              <p className="text-xs text-gray-400 mt-0.5">CARD-Net encountered an unexpected error</p>
            </div>
          </div>
          <p className="text-sm text-gray-300 font-mono bg-black/30 rounded-lg p-3 mb-5 break-all">
            {error.message || "Unknown error"}
          </p>
          <button
            onClick={reset}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
