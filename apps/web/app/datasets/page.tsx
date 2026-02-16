import Link from "next/link";
import { apiGet, type DatasetSummary } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function DatasetsPage(): Promise<React.JSX.Element> {
  const datasets = await apiGet<DatasetSummary[]>("/api/datasets");

  return (
    <section>
      <h1>Datasets</h1>
      <div className="grid grid-2">
        {datasets.map((dataset) => (
          <article className="card" key={dataset.slug}>
            <h3>{dataset.title}</h3>
            <p className="muted">Source: {dataset.source}</p>
            <Link href={`/datasets/${dataset.slug}`}>Open dataset</Link>
          </article>
        ))}
      </div>
    </section>
  );
}
