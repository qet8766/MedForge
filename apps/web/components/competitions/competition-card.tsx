import Link from "next/link";
import { Trophy } from "lucide-react";

import type { CompetitionSummary } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type CompetitionCardProps = {
  competition: CompetitionSummary;
};

export function CompetitionCard({ competition }: CompetitionCardProps): React.JSX.Element {
  return (
    <Link href={`/competitions/${competition.slug}`} className="group block">
      <Card className="h-full transition-colors group-hover:border-primary/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Trophy className="size-4 shrink-0 text-primary" />
            <span className="truncate">{competition.title}</span>
          </CardTitle>
          <div className="flex flex-wrap gap-1.5">
            <Badge variant={competition.competition_exposure === "internal" ? "outline" : "default"}>
              {competition.competition_exposure}
            </Badge>
            {competition.is_permanent ? (
              <Badge variant="secondary">Permanent</Badge>
            ) : null}
          </div>
        </CardHeader>

        <CardContent className="space-y-3">
          <p className="line-clamp-3 text-sm text-muted-foreground">
            {competition.description_preview}
          </p>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span>
              <span className="font-medium text-foreground">Metric:</span> {competition.metric}
            </span>
            <span>
              <span className="font-medium text-foreground">Cap:</span>{" "}
              {competition.submission_cap_per_day}/day
            </span>
            <span>
              <span className="font-medium text-foreground">Leaderboard:</span>{" "}
              {competition.leaderboard_rule}
            </span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
