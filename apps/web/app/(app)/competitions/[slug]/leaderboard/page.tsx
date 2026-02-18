import Link from "next/link";
import { Trophy } from "lucide-react";

import { apiGet, type LeaderboardResponse } from "@/lib/api";
import { inferServerSurface } from "@/lib/server-surface";
import { apiPathForSurface } from "@/lib/surface";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/feedback/empty-state";
import { LeaderboardTable } from "@/components/competitions/leaderboard-table";
import { LeaderboardChart } from "@/components/competitions/leaderboard-chart";

export const dynamic = "force-dynamic";

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

  if (leaderboard.entries.length === 0) {
    return (
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
    );
  }

  return (
    <div className="space-y-6">
      <LeaderboardChart entries={leaderboard.entries} />
      <LeaderboardTable entries={leaderboard.entries} competitionSlug={slug} />
    </div>
  );
}
