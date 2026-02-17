import { apiGet, type LeaderboardEntry } from "@/lib/api";
import { inferServerSurface } from "@/lib/server-surface";
import { apiPathForSurface } from "@/lib/surface";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const dynamic = "force-dynamic";

type LeaderboardResponse = {
  competition_slug: string;
  entries: LeaderboardEntry[];
};

export default async function CompetitionLeaderboardPage({
  params,
}: {
  params: { slug: string } | Promise<{ slug: string }>;
}): Promise<React.JSX.Element> {
  const resolvedParams = await params;
  const surface = await inferServerSurface();
  const leaderboard = await apiGet<LeaderboardResponse>(
    apiPathForSurface(surface, `/competitions/${resolvedParams.slug}/leaderboard`)
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Leaderboard</h1>
        <p className="text-muted-foreground">{leaderboard.competition_slug}</p>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-16">Rank</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Scored At</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {leaderboard.entries.map((entry) => (
                <TableRow key={entry.best_submission_id}>
                  <TableCell className="font-mono font-medium">{entry.rank}</TableCell>
                  <TableCell>{entry.user_id}</TableCell>
                  <TableCell className="font-mono">{entry.primary_score.toFixed(6)}</TableCell>
                  <TableCell className="text-muted-foreground">{entry.scored_at ?? "pending"}</TableCell>
                </TableRow>
              ))}
              {leaderboard.entries.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground">
                    No scored submissions yet.
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
