"use client";

interface StatusHeaderProps {
  healthStatus: "ok" | "degraded";
  loading: boolean;
}

export function StatusHeader({ healthStatus, loading }: StatusHeaderProps) {
  const isOk = healthStatus === "ok";

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <h1 className="font-mono text-2xl font-bold tracking-tight text-white">
          MedForge Server
        </h1>
        <div className="flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1">
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              isOk ? "bg-emerald-400" : "bg-amber-400"
            } ${loading ? "animate-pulse" : "animate-[pulse_2s_ease-in-out_infinite]"}`}
          />
          <span className="font-mono text-xs font-medium text-slate-300">
            {loading ? "LOADING" : isOk ? "LIVE" : "DEGRADED"}
          </span>
        </div>
      </div>
      <span className="font-mono text-xs text-slate-500">Status Page</span>
    </div>
  );
}
