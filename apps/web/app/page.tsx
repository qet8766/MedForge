import Link from "next/link";
import { apiGet, type CompetitionSummary } from "../lib/api";

export default async function HomePage(): Promise<JSX.Element> {
  const competitions = await apiGet<CompetitionSummary[]>("/api/competitions");

  return (
    <section className="grid" style={{ gap: 20 }}>
      <div className="card">
        <h1>MedForge Competitions</h1>
        <p className="muted">
          Permanent Kaggle-style competitions with code-server workflows and GPU-backed development sessions.
        </p>
        <Link href="/competitions">Browse competitions</Link>
      </div>
      <div className="grid grid-2">
        {competitions.map((competition) => (
          <article className="card" key={competition.slug}>
            <h3>{competition.title}</h3>
            <p className="muted">{competition.metric} · cap {competition.submission_cap_per_day}/day</p>
            <Link href={`/competitions/${competition.slug}`}>Open competition</Link>
          </article>
        ))}
      </div>
    </section>
  );
}
