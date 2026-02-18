"use client";

import type { GpuStatusData } from "@/lib/contracts";

interface GpuTooltipProps {
  gpu: GpuStatusData;
  position: { x: number; y: number };
}

export function GpuTooltip({ gpu, position }: GpuTooltipProps) {
  const isActive = gpu.session_status !== null;
  const vramPercent =
    gpu.memory_total_mib > 0
      ? ((gpu.memory_used_mib / gpu.memory_total_mib) * 100).toFixed(1)
      : "0.0";

  return (
    <div
      className="pointer-events-none absolute z-50 rounded-lg border border-white/10 bg-[#0f0f1a]/95 px-4 py-3 shadow-2xl backdrop-blur-sm"
      style={{
        left: position.x,
        top: position.y,
        transform: "translate(-50%, -100%) translateY(-12px)",
      }}
    >
      <div className="mb-2 flex items-center gap-2">
        <span className="font-mono text-xs font-semibold text-white">
          GPU {gpu.id}
        </span>
        <span className="font-mono text-xs text-slate-400">{gpu.name}</span>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 font-mono text-[11px]">
        <span className="text-slate-500">Utilization</span>
        <span className="text-right text-white">{gpu.utilization_percent}%</span>

        <span className="text-slate-500">VRAM</span>
        <span className="text-right text-white">
          {(gpu.memory_used_mib / 1024).toFixed(1)} / {(gpu.memory_total_mib / 1024).toFixed(1)} GB
          <span className="ml-1 text-slate-500">({vramPercent}%)</span>
        </span>

        <span className="text-slate-500">Temperature</span>
        <span className="text-right text-white">{gpu.temperature_celsius}&deg;C</span>

        <span className="text-slate-500">Power</span>
        <span className="text-right text-white">
          {gpu.power_draw_watts}W / {gpu.power_limit_watts}W
        </span>

        <span className="text-slate-500">Status</span>
        <span
          className={`text-right font-semibold ${
            isActive
              ? gpu.session_status === "running"
                ? "text-red-400"
                : "text-amber-400"
              : "text-slate-500"
          }`}
        >
          {gpu.session_status ?? "Idle"}
        </span>
      </div>
    </div>
  );
}
