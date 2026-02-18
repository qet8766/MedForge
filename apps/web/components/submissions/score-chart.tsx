"use client";

import { BarChart3 } from "lucide-react";
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import type { SubmissionRead } from "@/lib/api";
import { formatScore } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";

type ScoreChartProps = {
  submissions: SubmissionRead[];
};

type ScoreDataPoint = {
  date: string;
  score: number;
  filename: string;
};

const chartConfig = {
  score: {
    label: "Score",
    color: "var(--color-primary)",
  },
} satisfies ChartConfig;

function buildChartData(submissions: SubmissionRead[]): ScoreDataPoint[] {
  return submissions
    .filter((s) => s.score_status === "scored" && s.official_score !== null)
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
    .map((s) => ({
      date: new Date(s.created_at).toLocaleDateString(),
      score: s.official_score!.primary_score,
      filename: s.filename,
    }));
}

function formatYAxisTick(value: number): string {
  return formatScore(value, 2);
}

export function ScoreChart({ submissions }: ScoreChartProps): React.JSX.Element {
  const data = buildChartData(submissions);

  if (data.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center gap-3 py-12 text-center">
          <div className="flex size-12 items-center justify-center rounded-full bg-muted">
            <BarChart3 className="size-6 text-muted-foreground" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium">No scored submissions yet</p>
            <p className="text-xs text-muted-foreground">
              Score progression will appear here once submissions are scored.
            </p>
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
          Score Progression
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="h-64 w-full">
          <LineChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              fontSize={12}
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
                  labelFormatter={(label) => `Date: ${label}`}
                />
              }
            />
            <Line
              type="monotone"
              dataKey="score"
              stroke="var(--color-score)"
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
