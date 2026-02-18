"use client";

import type { StorageInfoData } from "@/lib/contracts";

interface StorageArrayProps {
  storage: StorageInfoData;
  x: number;
  y: number;
}

const DRIVE_COUNT = 4;
const BYTES_PER_TB = 1024 ** 4;

export function StorageArray({ storage, x, y }: StorageArrayProps) {
  const usagePercent = storage.usage_percent;
  const isOnline = storage.health === "ONLINE";
  const totalTb = (storage.total_bytes / BYTES_PER_TB).toFixed(1);
  const usedTb = (storage.used_bytes / BYTES_PER_TB).toFixed(1);

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
        STORAGE ARRAY
      </text>
      <text
        x={0}
        y={-42}
        textAnchor="middle"
        fill="#444"
        fontSize={6.5}
        fontFamily="var(--font-mono)"
      >
        4x 8TB NVMe
      </text>

      {/* Drive bays */}
      {Array.from({ length: DRIVE_COUNT }).map((_, i) => {
        const driveX = -54 + i * 28;
        const fillIntensity = 0.05 + (usagePercent / 100) * 0.25;
        return (
          <g key={i}>
            {/* Drive body */}
            <rect
              x={driveX}
              y={-24}
              width={22}
              height={50}
              rx={3}
              fill={`rgba(20, 184, 166, ${fillIntensity})`}
              stroke="#14b8a6"
              strokeWidth={0.75}
            />
            {/* Drive label */}
            <text
              x={driveX + 11}
              y={-4}
              textAnchor="middle"
              fill="#5eead4"
              fontSize={6}
              fontWeight={500}
              fontFamily="var(--font-mono)"
            >
              SSD
            </text>
            <text
              x={driveX + 11}
              y={8}
              textAnchor="middle"
              fill="#475569"
              fontSize={5}
              fontFamily="var(--font-mono)"
            >
              8TB
            </text>
            {/* Activity LED */}
            <circle
              cx={driveX + 11}
              cy={18}
              r={2}
              fill={isOnline ? "#14b8a6" : "#ef4444"}
              className={isOnline ? "animate-led-blink" : ""}
              style={{ animationDelay: `${i * 0.3}s` }}
            />
          </g>
        );
      })}

      {/* Usage text */}
      <text
        x={0}
        y={45}
        textAnchor="middle"
        fill="#14b8a6"
        fontSize={9}
        fontWeight={600}
        fontFamily="var(--font-mono)"
      >
        {usedTb} / {totalTb} TB
      </text>

      {/* Health badge */}
      <rect
        x={-30}
        y={52}
        width={60}
        height={14}
        rx={7}
        fill={isOnline ? "rgba(20, 184, 166, 0.1)" : "rgba(239, 68, 68, 0.1)"}
        stroke={isOnline ? "#14b8a6" : "#ef4444"}
        strokeWidth={0.5}
      />
      <circle
        cx={-16}
        cy={59}
        r={2}
        fill={isOnline ? "#14b8a6" : "#ef4444"}
      />
      <text
        x={4}
        y={62}
        textAnchor="middle"
        fill={isOnline ? "#5eead4" : "#f87171"}
        fontSize={6}
        fontWeight={500}
        fontFamily="var(--font-mono)"
      >
        RAIDZ1 {storage.health}
      </text>
    </g>
  );
}
