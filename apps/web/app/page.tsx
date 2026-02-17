import Link from "next/link";

import { apiGet, type CompetitionSummary, type MeResponse } from "@/lib/api";
import { inferServerSurface } from "@/lib/server-surface";
import { apiPathForSurface, surfaceHost } from "@/lib/surface";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export const dynamic = "force-dynamic";

export default async function HomePage(): Promise<React.JSX.Element> {
  const surface = await inferServerSurface();
  const competitions = await apiGet<CompetitionSummary[]>(apiPathForSurface(surface, "/competitions"));

  let me: MeResponse | null = null;
  try {
    me = await apiGet<MeResponse>("/api/v2/me");
  } catch {
    me = null;
  }

  const domain = process.env.NEXT_PUBLIC_DOMAIN?.trim() || process.env.DOMAIN?.trim() || "";
  const externalUrl = domain ? `https://${surfaceHost("external", domain)}` : "/competitions";
  const internalUrl = domain ? `https://${surfaceHost("internal", domain)}` : "/competitions";

  return (
    <div className="space-y-8">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">MedForge Competitions</CardTitle>
          <CardDescription>
            Exposure-separated competitions with GPU-backed development sessions.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Button size="lg" asChild>
            <a href={externalUrl}>EXTERNAL</a>
          </Button>
          {me?.can_use_internal ? (
            <Button size="lg" variant="secondary" asChild>
              <a href={internalUrl}>INTERNAL</a>
            </Button>
          ) : null}
          <Button variant="outline" asChild>
            <Link href="/competitions">Browse {surface.toUpperCase()} competitions</Link>
          </Button>
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        {competitions.map((competition) => (
          <Card key={competition.slug} className="transition-colors hover:border-primary/40">
            <CardHeader>
              <CardTitle>{competition.title}</CardTitle>
              <CardDescription className="flex items-center gap-2">
                <Badge variant="secondary">{competition.competition_exposure}</Badge>
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
