import type { CompetitionDetail } from "@/lib/api";
import { MetricDisplay } from "@/components/shared/metric-display";

type CompetitionStatsBarProps = {
  competition: CompetitionDetail;
  submissionCount?: number;
  rank?: number;
};

export function CompetitionStatsBar({
  competition,
  submissionCount,
  rank,
}: CompetitionStatsBarProps): React.JSX.Element {
  return (
    <div className="grid grid-cols-2 gap-6 rounded-lg border p-6 sm:grid-cols-3 lg:grid-cols-6">
      <MetricDisplay
        label="Metric"
        value={`${competition.metric} v${competition.metric_version}`}
      />
      <MetricDisplay
        label="Daily Cap"
        value={`${competition.submission_cap_per_day}/day`}
      />
      <MetricDisplay
        label="Scoring Mode"
        value={competition.scoring_mode}
      />
      <MetricDisplay
        label="Evaluation"
        value={competition.evaluation_policy}
      />
      {submissionCount !== undefined ? (
        <MetricDisplay
          label="My Submissions"
          value={submissionCount}
        />
      ) : null}
      {rank !== undefined ? (
        <MetricDisplay
          label="My Rank"
          value={`#${rank}`}
        />
      ) : null}
    </div>
  );
}
