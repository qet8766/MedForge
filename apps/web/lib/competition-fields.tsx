import Link from "next/link";

import type { CompetitionDetail } from "@/lib/api";

export type MetricField = {
  label: string;
  value: React.ReactNode;
};

export function buildMetricFields(competition: CompetitionDetail): MetricField[] {
  return [
    { label: "Metric", value: `${competition.metric} v${competition.metric_version}` },
    { label: "Scoring Mode", value: competition.scoring_mode },
    { label: "Leaderboard Rule", value: competition.leaderboard_rule },
    { label: "Evaluation Policy", value: competition.evaluation_policy },
    { label: "Daily Cap", value: `${competition.submission_cap_per_day} submissions` },
    {
      label: "Dataset",
      value: (
        <Link
          href={`/datasets/${competition.dataset_slug}`}
          className="text-primary underline underline-offset-4 hover:text-primary/80"
        >
          {competition.dataset_title}
        </Link>
      ),
    },
  ];
}
