import Link from "next/link";
import { apiGet, type CompetitionSummary } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function CompetitionsPage(): Promise<React.JSX.Element> {
  const competitions = await apiGet<CompetitionSummary[]>("/api/competitions");

  return (
    <section>
      <h1>Competitions</h1>
      <p className="muted">All alpha competitions are permanent and PUBLIC tier.</p>
      <div className="grid grid-2">
        {competitions.map((competition) => (
          <article className="card" key={competition.slug}>
            <h3>{competition.title}</h3>
            <p className="muted">
              Tier {competition.competition_tier} · {competition.metric} · {competition.submission_cap_per_day}/day
            </p>
            <div className="grid" style={{ gap: 8 }}>
              <Link href={`/competitions/${competition.slug}`}>Overview</Link>
              <Link href={`/competitions/${competition.slug}/leaderboard`}>Leaderboard</Link>
              <Link href={`/competitions/${competition.slug}/submit`}>Submit</Link>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
