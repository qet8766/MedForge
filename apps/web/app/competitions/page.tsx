import Link from "next/link";

import { apiGet, type CompetitionSummary } from "@/lib/api";
import { inferServerSurface } from "@/lib/server-surface";
import { apiPathForSurface } from "@/lib/surface";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export const dynamic = "force-dynamic";

export default async function CompetitionsPage(): Promise<React.JSX.Element> {
  const surface = await inferServerSurface();
  const competitions = await apiGet<CompetitionSummary[]>(apiPathForSurface(surface, "/competitions"));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Competitions</h1>
        <p className="text-muted-foreground">Active {surface.toUpperCase()} competitions.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {competitions.map((competition) => (
          <Card key={competition.slug} className="transition-colors hover:border-primary/40">
            <CardHeader>
              <CardTitle>{competition.title}</CardTitle>
              <CardDescription className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">{competition.competition_exposure}</Badge>
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
