"use client";

interface ConnectingLinesProps {
  cpuX: number;
  cpuY: number;
  gpuX: number;
  gpuY: number;
  ramX: number;
  ramY: number;
  storageX: number;
  storageY: number;
  gpuActive: boolean;
  ramActive: boolean;
  storageActive: boolean;
}

function DataLine({
  x1,
  y1,
  x2,
  y2,
  color,
  active,
  delay = 0,
}: {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  color: string;
  active: boolean;
  delay?: number;
}) {
  return (
    <line
      x1={x1}
      y1={y1}
      x2={x2}
      y2={y2}
      stroke={active ? color : "#1a1a2e"}
      strokeWidth={active ? 1.2 : 0.6}
      strokeDasharray="6 4"
      opacity={active ? 0.6 : 0.2}
      className={active ? "animate-data-flow" : ""}
      style={{ animationDelay: `${delay}s` }}
    />
  );
}

export function ConnectingLines({
  cpuX,
  cpuY,
  gpuX,
  gpuY,
  ramX,
  ramY,
  storageX,
  storageY,
  gpuActive,
  ramActive,
  storageActive,
}: ConnectingLinesProps) {
  return (
    <g>
      {/* CPU to GPU Array */}
      <DataLine
        x1={cpuX - 80}
        y1={cpuY + 10}
        x2={gpuX}
        y2={gpuY - 60}
        color="#ef4444"
        active={gpuActive}
        delay={0}
      />
      {/* CPU to RAM Bank */}
      <DataLine
        x1={cpuX}
        y1={cpuY + 55}
        x2={ramX}
        y2={ramY - 60}
        color="#22c55e"
        active={ramActive}
        delay={0.5}
      />
      {/* CPU to Storage */}
      <DataLine
        x1={cpuX + 80}
        y1={cpuY + 10}
        x2={storageX}
        y2={storageY - 60}
        color="#14b8a6"
        active={storageActive}
        delay={1}
      />
    </g>
  );
}
