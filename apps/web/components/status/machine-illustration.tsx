"use client";

import { useCallback, useRef, useState } from "react";

import type { GpuStatusData, ServerStatusResponse } from "@/lib/contracts";

import { GpuTooltip } from "./gpu-tooltip";
import { ConnectingLines } from "./svg/connecting-lines";
import { CpuChip } from "./svg/cpu-chip";
import { GpuArray } from "./svg/gpu-array";
import { RamBank } from "./svg/ram-bank";
import { StorageArray } from "./svg/storage-array";

interface MachineIllustrationProps {
  data: ServerStatusResponse;
}

// Layout positions in SVG coordinates
const CPU = { x: 400, y: 100 };
const GPU = { x: 170, y: 280 };
const RAM = { x: 400, y: 310 };
const STORAGE = { x: 630, y: 280 };

export function MachineIllustration({ data }: MachineIllustrationProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{
    gpu: GpuStatusData;
    position: { x: number; y: number };
  } | null>(null);

  const hasActiveGpu = data.sessions.gpus_in_use > 0;
  const hasRamUsage = data.system.ram_usage_percent > 0;
  const hasStorage = data.storage.total_bytes > 0;

  const handleGpuHover = useCallback(
    (gpu: GpuStatusData, rect: DOMRect) => {
      if (!containerRef.current) return;
      const containerRect = containerRef.current.getBoundingClientRect();
      setTooltip({
        gpu,
        position: {
          x: rect.left + rect.width / 2 - containerRect.left,
          y: rect.top - containerRect.top,
        },
      });
    },
    [],
  );

  const handleGpuLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  return (
    <div ref={containerRef} className="relative w-full">
      <svg
        viewBox="0 0 800 440"
        className="h-auto w-full"
        style={{ maxHeight: "70vh" }}
      >
        {/* Dark background */}
        <rect width={800} height={440} fill="#0a0a0f" rx={12} />

        {/* Subtle grid pattern */}
        <defs>
          <pattern
            id="grid"
            width={40}
            height={40}
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M 40 0 L 0 0 0 40"
              fill="none"
              stroke="#111122"
              strokeWidth={0.5}
            />
          </pattern>
        </defs>
        <rect width={800} height={440} fill="url(#grid)" rx={12} />

        {/* Connecting lines (behind components) */}
        <ConnectingLines
          cpuX={CPU.x}
          cpuY={CPU.y}
          gpuX={GPU.x}
          gpuY={GPU.y}
          ramX={RAM.x}
          ramY={RAM.y}
          storageX={STORAGE.x}
          storageY={STORAGE.y}
          gpuActive={hasActiveGpu}
          ramActive={hasRamUsage}
          storageActive={hasStorage}
        />

        {/* CPU */}
        <CpuChip system={data.system} x={CPU.x} y={CPU.y} />

        {/* GPU Array */}
        <GpuArray
          gpus={data.gpus}
          x={GPU.x}
          y={GPU.y}
          onGpuHover={handleGpuHover}
          onGpuLeave={handleGpuLeave}
        />

        {/* RAM Bank */}
        <RamBank system={data.system} x={RAM.x} y={RAM.y} />

        {/* Storage Array */}
        <StorageArray storage={data.storage} x={STORAGE.x} y={STORAGE.y} />
      </svg>

      {/* GPU Tooltip (positioned absolutely over SVG) */}
      {tooltip && (
        <GpuTooltip gpu={tooltip.gpu} position={tooltip.position} />
      )}
    </div>
  );
}
