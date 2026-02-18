import Link from "next/link";

import type { CompetitionDetail } from "@/lib/api";

type CompetitionStatsBarProps = {
  competition: CompetitionDetail;
};

export function CompetitionStatsBar({ competition }: CompetitionStatsBarProps): React.JSX.Element {
  return (
    <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted-foreground">
      <span>
        <span className="font-medium text-foreground">Metric:</span>{" "}
        {competition.metric} {competition.metric_version}
      </span>
      <span>
        <span className="font-medium text-foreground">Daily cap:</span>{" "}
        {competition.submission_cap_per_day} submissions
      </span>
      <span>
        <span className="font-medium text-foreground">Dataset:</span>{" "}
        <Link
          href={`/datasets/${competition.dataset_slug}`}
          className="text-primary underline underline-offset-4 hover:text-primary/80"
        >
          {competition.dataset_title}
        </Link>
      </span>
    </div>
  );
}
