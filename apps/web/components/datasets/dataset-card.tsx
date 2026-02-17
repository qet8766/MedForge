import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DatasetSummary } from "@/lib/api";

interface DatasetCardProps {
  dataset: DatasetSummary;
}

export function DatasetCard({ dataset }: DatasetCardProps): React.JSX.Element {
  return (
    <Link href={`/datasets/${dataset.slug}`} className="group">
      <Card className="transition-colors group-hover:border-primary/40">
        <CardHeader>
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-base">{dataset.title}</CardTitle>
            <Badge variant="secondary" className="shrink-0">
              {dataset.exposure}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{dataset.source}</p>
        </CardContent>
      </Card>
    </Link>
  );
}
