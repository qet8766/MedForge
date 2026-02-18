import { apiGet, type CompetitionDetail } from "@/lib/api";
import { inferServerSurface } from "@/lib/server-surface";
import { apiPathForSurface } from "@/lib/surface";
import { Badge } from "@/components/ui/badge";
import { CompetitionTabs } from "@/components/competitions/competition-tabs";
import { CompetitionStatsBar } from "@/components/competitions/competition-stats-bar";

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
        <p className="max-w-prose text-muted-foreground leading-relaxed">
          {competition.description}
        </p>
      </section>

      <CompetitionStatsBar competition={competition} />

      <CompetitionTabs slug={slug} />

      <div>{children}</div>
    </div>
  );
}
