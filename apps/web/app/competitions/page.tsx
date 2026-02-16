import Link from "next/link";

import { apiGet, type CompetitionSummary } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export const dynamic = "force-dynamic";

export default async function CompetitionsPage(): Promise<React.JSX.Element> {
  const competitions = await apiGet<CompetitionSummary[]>("/api/competitions");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Competitions</h1>
        <p className="text-muted-foreground">All alpha competitions are permanent and PUBLIC tier.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {competitions.map((competition) => (
          <Card key={competition.slug} className="transition-colors hover:border-primary/40">
            <CardHeader>
              <CardTitle>{competition.title}</CardTitle>
              <CardDescription className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">{competition.competition_tier}</Badge>
                <Badge variant="outline" className="font-mono text-xs">
                  {competition.metric}
                </Badge>
                <Badge variant="outline" className="font-mono text-xs">
                  {competition.scoring_mode}
                </Badge>
                <Badge variant="outline" className="font-mono text-xs">
                  {competition.leaderboard_rule}
                </Badge>
                <span>{competition.submission_cap_per_day}/day</span>
              </CardDescription>
            </CardHeader>
            <CardContent className="flex gap-3">
              <Button variant="link" className="h-auto p-0" asChild>
                <Link href={`/competitions/${competition.slug}`}>Overview</Link>
              </Button>
              <Button variant="link" className="h-auto p-0" asChild>
                <Link href={`/competitions/${competition.slug}/leaderboard`}>Leaderboard</Link>
              </Button>
              <Button variant="link" className="h-auto p-0" asChild>
                <Link href={`/competitions/${competition.slug}/submit`}>Submit</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
