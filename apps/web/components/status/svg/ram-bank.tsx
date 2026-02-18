"use client";

import type { SystemInfoData } from "@/lib/contracts";

interface RamBankProps {
  system: SystemInfoData;
  x: number;
  y: number;
}

const STICK_COUNT = 8;

export function RamBank({ system, x, y }: RamBankProps) {
  const usageRatio = system.ram_used_gib / system.ram_total_gib;
  const litSticks = Math.max(1, Math.ceil(usageRatio * STICK_COUNT));

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
        RAM BANK
      </text>
      <text
        x={0}
        y={-42}
        textAnchor="middle"
        fill="#444"
        fontSize={6.5}
        fontFamily="var(--font-mono)"
      >
        512 GB DDR5
      </text>

      {/* DIMM sticks */}
      {Array.from({ length: STICK_COUNT }).map((_, i) => {
        const isLit = i < litSticks;
        const stickX = -56 + i * 16;
        return (
          <g key={i}>
            {/* Stick body */}
            <rect
              x={stickX}
              y={-24}
              width={10}
              height={50}
              rx={2}
              fill={isLit ? "rgba(34, 197, 94, 0.15)" : "rgba(100, 100, 100, 0.05)"}
              stroke={isLit ? "#22c55e" : "#333"}
              strokeWidth={isLit ? 1.2 : 0.5}
            />
            {/* Chips on stick */}
            {[0, 1, 2, 3].map((chip) => (
              <rect
                key={chip}
                x={stickX + 2}
                y={-18 + chip * 12}
                width={6}
                height={8}
                rx={1}
                fill={isLit ? "rgba(34, 197, 94, 0.3)" : "rgba(100, 100, 100, 0.1)"}
              />
            ))}
            {/* Notch */}
            <rect
              x={stickX + 3}
              y={26}
              width={4}
              height={3}
              fill="#111"
            />
          </g>
        );
      })}

      {/* Usage text */}
      <text
        x={0}
        y={45}
        textAnchor="middle"
        fill="#22c55e"
        fontSize={9}
        fontWeight={600}
        fontFamily="var(--font-mono)"
      >
        {system.ram_used_gib.toFixed(0)} / {system.ram_total_gib.toFixed(0)} GB
      </text>
      <text
        x={0}
        y={58}
        textAnchor="middle"
        fill="#475569"
        fontSize={7}
        fontFamily="var(--font-mono)"
      >
        {system.ram_usage_percent.toFixed(1)}% used
      </text>
    </g>
  );
}
