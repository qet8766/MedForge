import { apiGet, type LeaderboardEntry } from "../../../../lib/api";

export const dynamic = "force-dynamic";

type LeaderboardResponse = {
  competition_slug: string;
  entries: LeaderboardEntry[];
};

export default async function CompetitionLeaderboardPage({
  params
}: {
  params: { slug: string };
}): Promise<React.JSX.Element> {
  const leaderboard = await apiGet<LeaderboardResponse>(
    `/api/competitions/${params.slug}/leaderboard`
  );

  return (
    <section>
      <h1>Leaderboard · {leaderboard.competition_slug}</h1>
      <table className="table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>User</th>
            <th>Score</th>
            <th>Scored At</th>
          </tr>
        </thead>
        <tbody>
          {leaderboard.entries.map((entry) => (
            <tr key={entry.best_submission_id}>
              <td>{entry.rank}</td>
              <td>{entry.user_id}</td>
              <td>{entry.leaderboard_score.toFixed(6)}</td>
              <td>{entry.scored_at ?? "pending"}</td>
            </tr>
          ))}
          {leaderboard.entries.length === 0 ? (
            <tr>
              <td colSpan={4}>No scored submissions yet.</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </section>
  );
}
