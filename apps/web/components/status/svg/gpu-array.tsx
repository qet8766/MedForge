"use client";

import type { GpuStatusData } from "@/lib/contracts";

interface GpuArrayProps {
  gpus: GpuStatusData[];
  x: number;
  y: number;
  onGpuHover: (gpu: GpuStatusData, rect: DOMRect) => void;
  onGpuLeave: () => void;
}

function GpuCard({
  gpu,
  index,
  onHover,
  onLeave,
}: {
  gpu: GpuStatusData;
  index: number;
  onHover: (gpu: GpuStatusData, rect: DOMRect) => void;
  onLeave: () => void;
}) {
  const isActive = gpu.session_status !== null;
  const isRunning = gpu.session_status === "running";
  const isStarting = gpu.session_status === "starting";

  const glowColor = isStarting
    ? "#f59e0b"
    : isActive
      ? "#ef4444"
      : "transparent";
  const strokeColor = isActive ? glowColor : "#333";
  const fillOpacity = isActive ? 0.15 : 0.03;
  const fillColor = isActive ? glowColor : "#666";
  const textColor = isActive ? (isStarting ? "#fbbf24" : "#f87171") : "#555";

  // Row layout: 4 on top, 3 on bottom
  const col = index < 4 ? index : index - 4;
  const row = index < 4 ? 0 : 1;
  const offsetX = col * 72 - (row === 0 ? 108 : 72);
  const offsetY = row * 80;

  return (
    <g
      transform={`translate(${offsetX}, ${offsetY})`}
      className="cursor-pointer"
      onMouseEnter={(e) => {
        const el = e.currentTarget as SVGGElement;
        const rect = el.getBoundingClientRect();
        onHover(gpu, rect);
      }}
      onMouseLeave={onLeave}
    >
      {/* Glow filter effect via drop-shadow */}
      {isActive && (
        <rect
          x={-28}
          y={-30}
          width={56}
          height={65}
          rx={6}
          fill="none"
          stroke={glowColor}
          strokeWidth={1}
          opacity={0.3}
          className={isRunning ? "animate-gpu-glow" : isStarting ? "animate-gpu-glow-amber" : ""}
        />
      )}

      {/* Card body */}
      <rect
        x={-24}
        y={-26}
        width={48}
        height={57}
        rx={4}
        fill={fillColor}
        fillOpacity={fillOpacity}
        stroke={strokeColor}
        strokeWidth={isActive ? 1.5 : 0.75}
      />

      {/* PCIe connector */}
      <rect x={-14} y={31} width={28} height={4} rx={1} fill={strokeColor} opacity={0.5} />

      {/* Power indicator */}
      <circle
        cx={16}
        cy={-18}
        r={2.5}
        fill={isActive ? glowColor : "#222"}
        stroke={isActive ? glowColor : "#444"}
        strokeWidth={0.5}
        className={isActive ? "animate-led-blink" : ""}
      />

      {/* GPU label */}
      <text
        x={0}
        y={-8}
        textAnchor="middle"
        fill={textColor}
        fontSize={8}
        fontWeight={600}
        fontFamily="var(--font-mono)"
      >
        GPU {gpu.id}
      </text>
      <text
        x={0}
        y={5}
        textAnchor="middle"
        fill={isActive ? textColor : "#444"}
        fontSize={5.5}
        fontFamily="var(--font-mono)"
      >
        RTX 5090
      </text>
      {isActive && (
        <text
          x={0}
          y={18}
          textAnchor="middle"
          fill={textColor}
          fontSize={5.5}
          fontWeight={500}
          fontFamily="var(--font-mono)"
          style={{ textTransform: "uppercase" }}
        >
          {gpu.session_status}
        </text>
      )}
    </g>
  );
}

export function GpuArray({ gpus, x, y, onGpuHover, onGpuLeave }: GpuArrayProps) {
  return (
    <g transform={`translate(${x}, ${y})`}>
      {/* Section label */}
      <text
        x={0}
        y={-55}
        textAnchor="middle"
        fill="#555"
        fontSize={8}
        fontWeight={500}
        fontFamily="var(--font-mono)"
        letterSpacing={2}
      >
        GPU ARRAY
      </text>
      <text
        x={0}
        y={-42}
        textAnchor="middle"
        fill="#444"
        fontSize={6.5}
        fontFamily="var(--font-mono)"
      >
        7x RTX 5090
      </text>

      {gpus.map((gpu, i) => (
        <GpuCard
          key={gpu.id}
          gpu={gpu}
          index={i}
          onHover={onGpuHover}
          onLeave={onGpuLeave}
        />
      ))}
    </g>
  );
}
