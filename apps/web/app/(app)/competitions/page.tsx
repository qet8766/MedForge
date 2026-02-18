import { Trophy } from "lucide-react";

import { apiGet, type CompetitionSummary } from "@/lib/api";
import { inferServerSurface } from "@/lib/server-surface";
import { apiPathForSurface } from "@/lib/surface";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/feedback/empty-state";
import { CompetitionCard } from "@/components/competitions/competition-card";
import { CompetitionFilters } from "@/components/competitions/competition-filters";

export const dynamic = "force-dynamic";

export default async function CompetitionsPage(): Promise<React.JSX.Element> {
  const surface = await inferServerSurface();
  const competitions = await apiGet<CompetitionSummary[]>(
    apiPathForSurface(surface, "/competitions"),
  );

  return (
    <div className="container mx-auto space-y-8 px-4 py-8">
      <PageHeader
        title="Competitions"
        description={`Showing ${surface.toUpperCase()} competitions`}
        actions={<CompetitionFilters />}
      />

      {competitions.length === 0 ? (
        <EmptyState
          icon={<Trophy className="size-5" />}
          title="No competitions"
          description="There are no competitions available on this surface yet."
        />
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-2">
          {competitions.map((competition) => (
            <CompetitionCard key={competition.slug} competition={competition} />
          ))}
        </div>
      )}
    </div>
  );
}
