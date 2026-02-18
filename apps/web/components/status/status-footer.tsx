"use client";

import type { PlatformStatsData } from "@/lib/contracts";

interface StatusFooterProps {
  platform: PlatformStatsData | null;
  lastUpdated: Date | null;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function StatusFooter({ platform, lastUpdated }: StatusFooterProps) {
  return (
    <div className="flex flex-col items-center gap-1 border-t border-white/5 pt-4 font-mono text-xs text-slate-500 sm:flex-row sm:justify-between">
      <div className="flex items-center gap-3">
        {platform && (
          <>
            <span>{platform.total_users} users</span>
            <span className="text-slate-700">&middot;</span>
            <span>{platform.total_competitions} competitions</span>
            <span className="text-slate-700">&middot;</span>
            <span>{platform.total_submissions} submissions</span>
          </>
        )}
      </div>
      <div className="flex items-center gap-2">
        {lastUpdated && (
          <span>Last updated {formatTime(lastUpdated)}</span>
        )}
        <span className="text-slate-700">&middot;</span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
          Auto-refreshing every 5s
        </span>
      </div>
    </div>
  );
}
