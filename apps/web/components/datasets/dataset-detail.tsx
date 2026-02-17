import type { DatasetDetail as DatasetDetailType } from "@/lib/api";

interface DatasetDetailProps {
  dataset: DatasetDetailType & { formattedSize: string };
}

export function DatasetDetail({ dataset }: DatasetDetailProps): React.JSX.Element {
  return (
    <dl className="grid gap-4 sm:grid-cols-2">
      <DetailEntry label="Source" value={dataset.source} />
      <DetailEntry label="License" value={dataset.license} />
      <DetailEntry label="Storage path" value={dataset.storage_path} mono />
      <DetailEntry label="Size" value={dataset.formattedSize} />
      <div className="sm:col-span-2">
        <DetailEntry label="Checksum" value={dataset.checksum} mono />
      </div>
    </dl>
  );
}

function DetailEntry({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}): React.JSX.Element {
  return (
    <div className="space-y-1">
      <dt className="text-sm font-medium text-muted-foreground">{label}</dt>
      <dd className={mono ? "break-all font-mono text-sm" : "text-sm"}>
        {value}
      </dd>
    </div>
  );
}
