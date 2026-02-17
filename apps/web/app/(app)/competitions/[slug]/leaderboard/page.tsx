import Link from "next/link";
import { ArrowLeft, Trophy } from "lucide-react";

import { apiGet, type LeaderboardEntry } from "@/lib/api";
import { inferServerSurface } from "@/lib/server-surface";
import { apiPathForSurface } from "@/lib/surface";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/feedback/empty-state";
import { LeaderboardTable } from "@/components/competitions/leaderboard-table";
import { LeaderboardChart } from "@/components/competitions/leaderboard-chart";

export const dynamic = "force-dynamic";

type LeaderboardResponse = {
  competition_slug: string;
  entries: LeaderboardEntry[];
};

export default async function LeaderboardPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<React.JSX.Element> {
  const { slug } = await params;
  const surface = await inferServerSurface();
  const leaderboard = await apiGet<LeaderboardResponse>(
    apiPathForSurface(surface, `/competitions/${slug}/leaderboard`),
  );

  return (
    <div className="container mx-auto space-y-8 px-4 py-8">
      <PageHeader
        title="Leaderboard"
        description={slug}
        actions={
          <Button variant="outline" size="sm" asChild>
            <Link href={`/competitions/${slug}`}>
              <ArrowLeft className="size-3.5" />
              Back to competition
            </Link>
          </Button>
        }
      />

      {leaderboard.entries.length === 0 ? (
        <EmptyState
          icon={<Trophy className="size-5" />}
          title="No submissions yet"
          description="Be the first to submit a solution and claim the top spot."
          action={
            <Button asChild>
              <Link href={`/competitions/${slug}/submit`}>Submit a solution</Link>
            </Button>
          }
        />
      ) : (
        <div className="space-y-6">
          <LeaderboardChart />
          <LeaderboardTable entries={leaderboard.entries} competitionSlug={slug} />
        </div>
      )}
    </div>
  );
}
