"use client";

import { useEffect, useState } from "react";

import { apiGet, type CompetitionSummary, type LeaderboardResponse } from "@/lib/api";
import { apiPathForSurface, inferClientSurface } from "@/lib/surface";
import { cn } from "@/lib/utils";
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

function rankBackground(rank: number): string | undefined {
  switch (rank) {
    case 1:
      return "bg-yellow-500/10";
    case 2:
      return "bg-zinc-400/10";
    case 3:
      return "bg-amber-700/10";
    default:
      return undefined;
  }
}

function rankLabel(rank: number): string {
  switch (rank) {
    case 1:
      return "\ud83e\udd47";
    case 2:
      return "\ud83e\udd48";
    case 3:
      return "\ud83e\udd49";
    default:
      return String(rank);
  }
}

function formatScoredAt(scoredAt: string | null): string {
  if (scoredAt === null) {
    return "pending";
  }
  return new Date(scoredAt).toLocaleString();
}

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
  const [rankings, setRankings] = useState<RankedUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetchGlobalRankings()
      .then((data) => {
        if (!cancelled) {
          setRankings(data);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Failed to load rankings.";
          setError(message);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <LoadingSkeleton />;
  }

  if (error !== null) {
    return (
      <div className="py-8 text-center text-sm text-destructive">
        {error}
      </div>
    );
  }

  if (rankings.length === 0) {
    return (
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Rank</TableHead>
            <TableHead>User</TableHead>
            <TableHead className="text-right">Best Score</TableHead>
            <TableHead>Competition</TableHead>
            <TableHead className="text-right">Scored At</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
              No ranked users yet. Scores will appear once competitions receive submissions.
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
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
        {rankings.map((user, index) => {
          const rank = index + 1;
          return (
            <TableRow key={user.userId} className={cn(rankBackground(rank))}>
              <TableCell className="font-medium">{rankLabel(rank)}</TableCell>
              <TableCell className="font-mono text-sm">{user.userId}</TableCell>
              <TableCell className="text-right font-mono tabular-nums">
                {user.bestScore.toFixed(6)}
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
