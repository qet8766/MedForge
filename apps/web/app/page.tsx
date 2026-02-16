import Link from "next/link";

import { apiGet, type CompetitionSummary } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export const dynamic = "force-dynamic";

export default async function HomePage(): Promise<React.JSX.Element> {
  const competitions = await apiGet<CompetitionSummary[]>("/api/competitions");

  return (
    <div className="space-y-8">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">MedForge Competitions</CardTitle>
          <CardDescription>
            Permanent Kaggle-style competitions with code-server workflows and GPU-backed development sessions.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link href="/competitions">Browse competitions</Link>
          </Button>
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        {competitions.map((competition) => (
          <Card key={competition.slug} className="transition-colors hover:border-primary/40">
            <CardHeader>
              <CardTitle>{competition.title}</CardTitle>
              <CardDescription className="flex items-center gap-2">
                <Badge variant="outline" className="font-mono text-xs">
                  {competition.metric}
                </Badge>
                <span>cap {competition.submission_cap_per_day}/day</span>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="link" className="h-auto p-0" asChild>
                <Link href={`/competitions/${competition.slug}`}>Open competition</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
