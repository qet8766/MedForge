"use client";

import { useEffect } from "react";

import { apiGet, type CompetitionSummary, type LeaderboardResponse } from "@/lib/api";
import { formatScore, getErrorMessage } from "@/lib/format";
import { useFetchState } from "@/lib/hooks/use-fetch-state";
import { formatScoredAt, rankBackground, rankLabel } from "@/lib/leaderboard-utils";
import { apiPathForSurface, inferClientSurface } from "@/lib/surface";
import { cn } from "@/lib/utils";
import { TableEmptyState, TableErrorState } from "@/components/shared/table-states";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type RankedUser = {
  userId: string;
  bestScore: number;
  competitionSlug: string;
  competitionTitle: string;
  scoredAt: string | null;
};

async function fetchGlobalRankings(): Promise<RankedUser[]> {
  const surface = inferClientSurface();
  const competitions = await apiGet<CompetitionSummary[]>(
    apiPathForSurface(surface, "/competitions"),
  );

  const leaderboardPromises = competitions.map(async (comp) => {
    const leaderboard = await apiGet<LeaderboardResponse>(
      apiPathForSurface(surface, `/competitions/${comp.slug}/leaderboard`),
    );
    return { competition: comp, entries: leaderboard.entries };
  });

  const results = await Promise.allSettled(leaderboardPromises);

  const bestByUser = new Map<string, RankedUser>();

  for (const result of results) {
    if (result.status !== "fulfilled") {
      continue;
    }
    const { competition, entries } = result.value;
    for (const entry of entries) {
      const existing = bestByUser.get(entry.user_id);
      if (existing === undefined || entry.primary_score > existing.bestScore) {
        bestByUser.set(entry.user_id, {
          userId: entry.user_id,
          bestScore: entry.primary_score,
          competitionSlug: competition.slug,
          competitionTitle: competition.title,
          scoredAt: entry.scored_at,
        });
      }
    }
  }

  const ranked = Array.from(bestByUser.values());
  ranked.sort((a, b) => b.bestScore - a.bestScore);
  return ranked;
}

function LoadingSkeleton(): React.JSX.Element {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }, (_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}

export function GlobalLeaderboard(): React.JSX.Element {
  const [state, setState] = useFetchState<RankedUser[]>([]);

  useEffect(() => {
    let cancelled = false;

    fetchGlobalRankings()
      .then((data) => {
        if (!cancelled) {
          setState({ data, loading: false, error: null });
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = getErrorMessage(err, "Failed to load rankings.");
          setState({ data: [], loading: false, error: message });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [setState]);

  if (state.loading) {
    return <LoadingSkeleton />;
  }

  if (state.error !== null) {
    return <TableErrorState message={state.error} />;
  }

  if (state.data.length === 0) {
    return <TableEmptyState message="No ranked users yet. Scores will appear once competitions receive submissions." />;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-16">Rank</TableHead>
          <TableHead>User</TableHead>
          <TableHead className="text-right">Best Score</TableHead>
          <TableHead>Competition</TableHead>
          <TableHead className="text-right">Scored At</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {state.data.map((user, index) => {
          const rank = index + 1;
          return (
            <TableRow key={user.userId} className={cn(rankBackground(rank))}>
              <TableCell className="font-medium">{rankLabel(rank)}</TableCell>
              <TableCell className="font-mono text-sm">{user.userId}</TableCell>
              <TableCell className="text-right font-mono tabular-nums">
                {formatScore(user.bestScore, 6)}
              </TableCell>
              <TableCell className="text-sm">{user.competitionTitle}</TableCell>
              <TableCell className="text-right text-sm text-muted-foreground">
                {formatScoredAt(user.scoredAt)}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
