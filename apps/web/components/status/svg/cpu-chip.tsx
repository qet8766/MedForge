"use client";

import type { SystemInfoData } from "@/lib/contracts";

interface CpuChipProps {
  system: SystemInfoData;
  x: number;
  y: number;
}

export function CpuChip({ system, x, y }: CpuChipProps) {
  const load = system.cpu_usage_percent;
  // Pulse speed: inversely proportional to load (faster = higher load)
  const pulseDuration = load > 5 ? Math.max(0.4, 2.5 - load / 50) : 3;
  const pulseOpacity = Math.min(0.15 + load / 100, 0.9);
  const fillOpacity = 0.05 + (load / 100) * 0.4;

  return (
    <g transform={`translate(${x}, ${y})`}>
      {/* Pulse rings */}
      <rect
        x={-80}
        y={-55}
        width={160}
        height={110}
        rx={12}
        fill="none"
        stroke="#3b82f6"
        strokeWidth={1.5}
        opacity={pulseOpacity}
        className="animate-cpu-pulse"
        style={{ animationDuration: `${pulseDuration}s` }}
      />
      <rect
        x={-88}
        y={-63}
        width={176}
        height={126}
        rx={16}
        fill="none"
        stroke="#3b82f6"
        strokeWidth={1}
        opacity={pulseOpacity * 0.5}
        className="animate-cpu-pulse"
        style={{ animationDuration: `${pulseDuration * 1.3}s` }}
      />

      {/* Chip body */}
      <rect
        x={-70}
        y={-45}
        width={140}
        height={90}
        rx={8}
        fill={`rgba(59, 130, 246, ${fillOpacity})`}
        stroke="#3b82f6"
        strokeWidth={1.5}
      />

      {/* Pin rows top */}
      {Array.from({ length: 8 }).map((_, i) => (
        <rect
          key={`pin-t-${i}`}
          x={-56 + i * 16}
          y={-52}
          width={4}
          height={7}
          rx={1}
          fill="#3b82f6"
          opacity={0.5}
        />
      ))}
      {/* Pin rows bottom */}
      {Array.from({ length: 8 }).map((_, i) => (
        <rect
          key={`pin-b-${i}`}
          x={-56 + i * 16}
          y={45}
          width={4}
          height={7}
          rx={1}
          fill="#3b82f6"
          opacity={0.5}
        />
      ))}
      {/* Pin rows left */}
      {Array.from({ length: 4 }).map((_, i) => (
        <rect
          key={`pin-l-${i}`}
          x={-77}
          y={-28 + i * 18}
          width={7}
          height={4}
          rx={1}
          fill="#3b82f6"
          opacity={0.5}
        />
      ))}
      {/* Pin rows right */}
      {Array.from({ length: 4 }).map((_, i) => (
        <rect
          key={`pin-r-${i}`}
          x={70}
          y={-28 + i * 18}
          width={7}
          height={4}
          rx={1}
          fill="#3b82f6"
          opacity={0.5}
        />
      ))}

      {/* CPU label */}
      <text
        x={0}
        y={-14}
        textAnchor="middle"
        fill="#93c5fd"
        fontSize={11}
        fontWeight={600}
        fontFamily="var(--font-mono)"
      >
        CPU
      </text>
      <text
        x={0}
        y={2}
        textAnchor="middle"
        fill="#64748b"
        fontSize={7.5}
        fontFamily="var(--font-mono)"
      >
        TR PRO 9985WX
      </text>
      <text
        x={0}
        y={16}
        textAnchor="middle"
        fill="#475569"
        fontSize={7}
        fontFamily="var(--font-mono)"
      >
        {system.cpu_cores}C / {system.cpu_count}T
      </text>
      <text
        x={0}
        y={32}
        textAnchor="middle"
        fill="#3b82f6"
        fontSize={9}
        fontWeight={600}
        fontFamily="var(--font-mono)"
      >
        {load.toFixed(1)}%
      </text>
    </g>
  );
}
