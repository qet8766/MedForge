import { apiGet, type DatasetDetail as DatasetDetailType } from "@/lib/api";
import { formatBytes } from "@/lib/format";
import { inferServerSurface } from "@/lib/server-surface";
import { apiPathForSurface } from "@/lib/surface";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { DatasetDetail } from "@/components/datasets/dataset-detail";
import { DatasetExplorer } from "@/components/datasets/dataset-explorer";
import { PageHeader } from "@/components/layout/page-header";

export const dynamic = "force-dynamic";

export default async function DatasetSlugPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<React.JSX.Element> {
  const { slug } = await params;
  const surface = await inferServerSurface();
  const dataset = await apiGet<DatasetDetailType>(
    apiPathForSurface(surface, `/datasets/${slug}`),
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title={dataset.title}
        actions={<Badge variant="secondary">{dataset.exposure}</Badge>}
      />

      <Card>
        <CardContent className="pt-6">
          <DatasetDetail
            dataset={{ ...dataset, formattedSize: formatBytes(dataset.bytes) }}
          />
        </CardContent>
      </Card>

      <DatasetExplorer slug={slug} />
    </div>
  );
}
