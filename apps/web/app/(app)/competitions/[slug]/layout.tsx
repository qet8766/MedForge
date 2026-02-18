import Link from "next/link";

import { apiGet, type CompetitionDetail } from "@/lib/api";
import { inferServerSurface } from "@/lib/server-surface";
import { apiPathForSurface } from "@/lib/surface";
import { Badge } from "@/components/ui/badge";
import { CompetitionTabs } from "@/components/competitions/competition-tabs";

export const dynamic = "force-dynamic";

type CompetitionSlugLayoutProps = {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
};

export default async function CompetitionSlugLayout({
  children,
  params,
}: CompetitionSlugLayoutProps): Promise<React.JSX.Element> {
  const { slug } = await params;
  const surface = await inferServerSurface();
  const competition = await apiGet<CompetitionDetail>(
    apiPathForSurface(surface, `/competitions/${slug}`),
  );

  return (
    <div className="container mx-auto space-y-6 px-4 py-8">
      <section className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight">{competition.title}</h1>
          <Badge variant={competition.competition_exposure === "internal" ? "outline" : "default"}>
            {competition.competition_exposure}
          </Badge>
          {competition.is_permanent ? (
            <Badge variant="secondary">Permanent</Badge>
          ) : null}
          <Badge variant="secondary">{competition.status}</Badge>
        </div>
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
      </section>

      <CompetitionTabs slug={slug} />

      <div>{children}</div>
    </div>
  );
}
