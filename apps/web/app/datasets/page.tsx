import Link from "next/link";

import { apiGet, type DatasetSummary } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export const dynamic = "force-dynamic";

export default async function DatasetsPage(): Promise<React.JSX.Element> {
  const datasets = await apiGet<DatasetSummary[]>("/api/datasets");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Datasets</h1>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {datasets.map((dataset) => (
          <Card key={dataset.slug} className="transition-colors hover:border-primary/40">
            <CardHeader>
              <CardTitle>{dataset.title}</CardTitle>
              <CardDescription>Source: {dataset.source}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="link" className="h-auto p-0" asChild>
                <Link href={`/datasets/${dataset.slug}`}>Open dataset</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
