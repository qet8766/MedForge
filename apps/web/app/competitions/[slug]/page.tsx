import Link from "next/link";
import { apiGet, type CompetitionDetail } from "../../../lib/api";

export const dynamic = "force-dynamic";

export default async function CompetitionDetailPage({
  params
}: {
  params: { slug: string };
}): Promise<React.JSX.Element> {
  const competition = await apiGet<CompetitionDetail>(`/api/competitions/${params.slug}`);

  return (
    <section className="grid" style={{ gap: 16 }}>
      <div className="card">
        <h1>{competition.title}</h1>
        <p className="muted">{competition.description}</p>
        <p>
          <strong>Competition Tier:</strong> {competition.competition_tier}
        </p>
        <p>
          <strong>Metric:</strong> {competition.metric}
        </p>
        <p>
          <strong>Daily Cap:</strong> {competition.submission_cap_per_day}
        </p>
        <p>
          <strong>Dataset:</strong> <Link href={`/datasets/${competition.dataset_slug}`}>{competition.dataset_title}</Link>
        </p>
      </div>
      <div className="card">
        <h3>Actions</h3>
        <div className="grid" style={{ gap: 8 }}>
          <Link href={`/competitions/${competition.slug}/leaderboard`}>View leaderboard</Link>
          <Link href={`/competitions/${competition.slug}/submit`}>Submit predictions</Link>
          <Link href="/sessions">Open code-server workspace</Link>
        </div>
      </div>
    </section>
  );
}
