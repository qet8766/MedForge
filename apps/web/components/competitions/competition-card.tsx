import Link from "next/link";
import { BarChart3, Trophy, Upload } from "lucide-react";

import type { CompetitionSummary } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricBadge } from "@/components/competitions/metric-badge";

type CompetitionCardProps = {
  competition: CompetitionSummary;
};

function exposureVariant(exposure: string): "default" | "outline" {
  if (exposure === "internal") {
    return "outline";
  }
  return "default";
}

export function CompetitionCard({ competition }: CompetitionCardProps): React.JSX.Element {
  return (
    <Card className="transition-colors hover:border-primary/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Trophy className="size-4 shrink-0 text-primary" />
          <span className="truncate">{competition.title}</span>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-1.5">
          <Badge variant={exposureVariant(competition.competition_exposure)}>
            {competition.competition_exposure}
          </Badge>
          <MetricBadge label="metric" value={competition.metric} />
          <MetricBadge label="scoring" value={competition.scoring_mode} />
          <MetricBadge label="leaderboard" value={competition.leaderboard_rule} />
        </div>
        <p className="text-xs text-muted-foreground">
          {competition.submission_cap_per_day} submissions / day
          {competition.is_permanent ? " \u00b7 Permanent" : ""}
        </p>
      </CardContent>

      <CardFooter className="gap-2">
        <Button variant="outline" size="sm" asChild>
          <Link href={`/competitions/${competition.slug}`}>
            <Trophy className="size-3.5" />
            Overview
          </Link>
        </Button>
        <Button variant="outline" size="sm" asChild>
          <Link href={`/competitions/${competition.slug}/leaderboard`}>
            <BarChart3 className="size-3.5" />
            Leaderboard
          </Link>
        </Button>
        <Button variant="ghost" size="sm" asChild>
          <Link href={`/competitions/${competition.slug}/submit`}>
            <Upload className="size-3.5" />
            Submit
          </Link>
        </Button>
      </CardFooter>
    </Card>
  );
}
