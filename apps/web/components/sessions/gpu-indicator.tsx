import { Badge } from "@/components/ui/badge";

type GpuIndicatorProps = {
  gpuId: number;
  status: string;
};

function gpuBadgeVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "running":
      return "default";
    case "starting":
      return "outline";
    case "stopped":
    case "stopping":
      return "secondary";
    case "error":
      return "destructive";
    default:
      return "outline";
  }
}

export function GpuIndicator({ gpuId, status }: GpuIndicatorProps): React.JSX.Element {
  return (
    <span className="inline-flex items-center gap-2">
      <span className="text-sm text-muted-foreground">GPU</span>
      <Badge variant={gpuBadgeVariant(status)}>
        <span className="font-mono">{gpuId}</span>
      </Badge>
    </span>
  );
}
