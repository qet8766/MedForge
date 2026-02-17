"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";

const EXPOSURE_OPTIONS = ["all", "external", "internal"] as const;
type ExposureFilter = (typeof EXPOSURE_OPTIONS)[number];

export function CompetitionFilters(): React.JSX.Element {
  const [selected, setSelected] = useState<ExposureFilter>("all");

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs font-medium text-muted-foreground">Filter:</span>
      {EXPOSURE_OPTIONS.map((option) => (
        <button key={option} type="button" onClick={() => setSelected(option)}>
          <Badge
            variant={selected === option ? "default" : "outline"}
            className="cursor-pointer"
          >
            {option}
          </Badge>
        </button>
      ))}
    </div>
  );
}
