import Link from "next/link";

import { apiGet, type CompetitionDetail } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

export const dynamic = "force-dynamic";

export default async function CompetitionDetailPage({
  params,
}: {
  params: { slug: string } | Promise<{ slug: string }>;
}): Promise<React.JSX.Element> {
  const resolvedParams = await params;
  const competition = await apiGet<CompetitionDetail>(`/api/competitions/${resolvedParams.slug}`);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle className="text-2xl">{competition.title}</CardTitle>
            <Badge variant="secondary">{competition.competition_tier}</Badge>
          </div>
          <CardDescription>{competition.description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <p className="text-sm text-muted-foreground">Metric</p>
              <p className="font-mono text-sm font-medium">{competition.metric}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Scoring Mode</p>
              <p className="font-mono text-sm font-medium">{competition.scoring_mode}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Leaderboard Rule</p>
              <p className="font-mono text-sm font-medium">{competition.leaderboard_rule}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Evaluation Policy</p>
              <p className="font-mono text-sm font-medium">{competition.evaluation_policy}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Daily Cap</p>
              <p className="font-mono text-sm font-medium">{competition.submission_cap_per_day}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Dataset</p>
              <Button variant="link" className="h-auto p-0 text-sm" asChild>
                <Link href={`/datasets/${competition.dataset_slug}`}>{competition.dataset_title}</Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <Button variant="outline" asChild>
              <Link href={`/competitions/${competition.slug}/leaderboard`}>View leaderboard</Link>
            </Button>
            <Button asChild>
              <Link href={`/competitions/${competition.slug}/submit`}>Submit predictions</Link>
            </Button>
            <Separator orientation="vertical" className="mx-1 h-9" />
            <Button variant="secondary" asChild>
              <Link href="/sessions">Open code-server workspace</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
