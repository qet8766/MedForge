"use client";

import { BarChart3 } from "lucide-react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";

import type { LeaderboardEntry } from "@/lib/api";
import { formatScore } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";

type LeaderboardChartProps = {
  entries: LeaderboardEntry[];
  maxEntries?: number;
};

type ChartDataPoint = {
  user: string;
  score: number;
  rank: number;
};

const chartConfig = {
  score: {
    label: "Score",
    color: "var(--color-primary)",
  },
} satisfies ChartConfig;

function buildChartData(entries: LeaderboardEntry[], maxEntries: number): ChartDataPoint[] {
  return entries
    .slice(0, maxEntries)
    .map((entry) => ({
      user: entry.user_id.length > 10
        ? `${entry.user_id.slice(0, 8)}...`
        : entry.user_id,
      score: entry.primary_score,
      rank: entry.rank,
    }));
}

function formatYAxisTick(value: number): string {
  return formatScore(value, 2);
}

export function LeaderboardChart({
  entries,
  maxEntries = 10,
}: LeaderboardChartProps): React.JSX.Element {
  const data = buildChartData(entries, maxEntries);

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <BarChart3 className="size-4" />
            Score Distribution
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
            No scores to display yet.
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <BarChart3 className="size-4" />
          Score Distribution (Top {data.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="h-64 w-full">
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="user"
              tickLine={false}
              axisLine={false}
              fontSize={11}
              angle={-30}
              textAnchor="end"
              height={60}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              fontSize={12}
              tickFormatter={formatYAxisTick}
              domain={["auto", "auto"]}
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  labelFormatter={(label) => `User: ${label}`}
                />
              }
            />
            <Bar
              dataKey="score"
              fill="var(--color-score)"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
