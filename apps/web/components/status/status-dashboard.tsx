"use client";

import { useCallback, useEffect, useState } from "react";

import { apiGet, type ServerStatusResponse } from "@/lib/api";
import { getErrorMessage } from "@/lib/format";
import { usePolling } from "@/lib/hooks/use-polling";

import { MachineIllustration } from "./machine-illustration";
import { StatusFooter } from "./status-footer";
import { StatusHeader } from "./status-header";

export function StatusDashboard() {
  const [data, setData] = useState<ServerStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const result = await apiGet<ServerStatusResponse>("/api/v2/status");
      setData(result);
      setError(null);
      setLastUpdated(new Date());
    } catch (err) {
      setError(getErrorMessage(err, "Failed to fetch server status"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  usePolling(fetchStatus, 5000, !loading);

  if (loading && !data) {
    return (
      <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
        <StatusHeader healthStatus="ok" loading={true} />
        <div className="flex h-[60vh] items-center justify-center rounded-xl border border-white/5 bg-[#0a0a0f]">
          <div className="flex flex-col items-center gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
            <span className="font-mono text-sm text-slate-500">
              Connecting to server...
            </span>
          </div>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
        <StatusHeader healthStatus="degraded" loading={false} />
        <div className="flex h-[40vh] items-center justify-center rounded-xl border border-red-500/20 bg-[#0a0a0f]">
          <div className="flex flex-col items-center gap-3 text-center">
            <div className="rounded-full bg-red-500/10 p-3">
              <svg
                className="h-6 w-6 text-red-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <p className="font-mono text-sm text-red-400">{error}</p>
            <button
              onClick={fetchStatus}
              className="mt-2 rounded-md border border-white/10 bg-white/5 px-4 py-1.5 font-mono text-xs text-slate-300 transition hover:bg-white/10"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <StatusHeader healthStatus={data.health_status} loading={loading} />

      {error && (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-2 font-mono text-xs text-amber-400">
          Connection issue: {error} &mdash; showing last known data
        </div>
      )}

      <MachineIllustration data={data} />

      <StatusFooter platform={data.platform} lastUpdated={lastUpdated} />
    </div>
  );
}
