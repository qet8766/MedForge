import { Database } from "lucide-react";

import { apiGet, type DatasetSummary } from "@/lib/api";
import { inferServerSurface } from "@/lib/server-surface";
import { apiPathForSurface } from "@/lib/surface";
import { DatasetCard } from "@/components/datasets/dataset-card";
import { EmptyState } from "@/components/feedback/empty-state";
import { PageHeader } from "@/components/layout/page-header";

export const dynamic = "force-dynamic";

export default async function DatasetsPage(): Promise<React.JSX.Element> {
  const surface = await inferServerSurface();
  const datasets = await apiGet<DatasetSummary[]>(
    apiPathForSurface(surface, "/datasets"),
  );

  return (
    <div className="space-y-6">
      <PageHeader title="Datasets" description="Browse available datasets" />

      {datasets.length === 0 ? (
        <EmptyState
          icon={<Database className="size-5" />}
          title="No datasets"
          description="No datasets are available yet."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {datasets.map((dataset) => (
            <DatasetCard key={dataset.slug} dataset={dataset} />
          ))}
        </div>
      )}
    </div>
  );
}
