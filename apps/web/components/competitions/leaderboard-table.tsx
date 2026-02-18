import type { LeaderboardEntry } from "@/lib/api";
import { formatScore } from "@/lib/format";
import { formatScoredAt, rankBackground, rankLabel } from "@/lib/leaderboard-utils";
import { cn } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type LeaderboardTableProps = {
  entries: LeaderboardEntry[];
  competitionSlug: string;
};

export function LeaderboardTable({ entries, competitionSlug }: LeaderboardTableProps): React.JSX.Element {
  if (entries.length === 0) {
    return (
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Rank</TableHead>
            <TableHead>User</TableHead>
            <TableHead className="text-right">Score</TableHead>
            <TableHead className="text-right">Scored At</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
              No entries yet for {competitionSlug}.
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
          <TableHead className="text-right">Score</TableHead>
          <TableHead className="text-right">Scored At</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {entries.map((entry) => (
          <TableRow key={entry.best_score_id} className={cn(rankBackground(entry.rank))}>
            <TableCell className="font-medium">{rankLabel(entry.rank)}</TableCell>
            <TableCell className="font-mono text-sm">{entry.user_id}</TableCell>
            <TableCell className="text-right font-mono tabular-nums">
              {formatScore(entry.primary_score, 6)}
            </TableCell>
            <TableCell className="text-right text-sm text-muted-foreground">
              {formatScoredAt(entry.scored_at)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
