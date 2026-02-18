"use client";

import { useState } from "react";

import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

const EXPOSURE_OPTIONS = ["all", "external", "internal"] as const;
type ExposureFilter = (typeof EXPOSURE_OPTIONS)[number];

export function CompetitionFilters(): React.JSX.Element {
  const [selected, setSelected] = useState<ExposureFilter>("all");

  function handleValueChange(value: string): void {
    if (value) {
      setSelected(value as ExposureFilter);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <span className="text-xs font-medium text-muted-foreground">Filter:</span>
      <ToggleGroup
        type="single"
        value={selected}
        onValueChange={handleValueChange}
        variant="outline"
        size="sm"
      >
        {EXPOSURE_OPTIONS.map((option) => (
          <ToggleGroupItem key={option} value={option} aria-label={`Filter by ${option}`}>
            {option}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </div>
  );
}
