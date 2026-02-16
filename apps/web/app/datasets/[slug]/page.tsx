import { apiGet, type DatasetDetail } from "../../../lib/api";

export const dynamic = "force-dynamic";

export default async function DatasetDetailPage({
  params
}: {
  params: { slug: string };
}): Promise<React.JSX.Element> {
  const dataset = await apiGet<DatasetDetail>(`/api/datasets/${params.slug}`);

  return (
    <section className="card" style={{ maxWidth: 760 }}>
      <h1>{dataset.title}</h1>
      <p>
        <strong>Source:</strong> {dataset.source}
      </p>
      <p>
        <strong>License:</strong> {dataset.license}
      </p>
      <p>
        <strong>Storage Path:</strong> {dataset.storage_path}
      </p>
      <p>
        <strong>Bytes:</strong> {dataset.bytes}
      </p>
      <p>
        <strong>Checksum:</strong> {dataset.checksum}
      </p>
    </section>
  );
}
