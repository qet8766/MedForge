import { apiGet, type DatasetDetail } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const dynamic = "force-dynamic";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes;
  let unitIndex = -1;
  do {
    value /= 1024;
    unitIndex++;
  } while (value >= 1024 && unitIndex < units.length - 1);
  return `${value.toFixed(1)} ${units[unitIndex]}`;
}

export default async function DatasetDetailPage({
  params,
}: {
  params: { slug: string };
}): Promise<React.JSX.Element> {
  const dataset = await apiGet<DatasetDetail>(`/api/datasets/${params.slug}`);

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{dataset.title}</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Dataset Details</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-sm text-muted-foreground">Source</dt>
              <dd className="text-sm font-medium">{dataset.source}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">License</dt>
              <dd className="text-sm font-medium">{dataset.license}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Storage Path</dt>
              <dd className="font-mono text-sm">{dataset.storage_path}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Size</dt>
              <dd className="font-mono text-sm font-medium">{formatBytes(dataset.bytes)}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-sm text-muted-foreground">Checksum</dt>
              <dd className="font-mono text-xs break-all">{dataset.checksum}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
