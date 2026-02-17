import type { SessionRead } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { GpuIndicator } from "@/components/sessions/gpu-indicator";

type SessionCardProps = {
  session: SessionRead;
};

function statusVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
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

function formatTimestamp(value: string | null): string {
  if (value === null) {
    return "--";
  }
  return new Date(value).toLocaleString();
}

export function SessionCard({ session }: SessionCardProps): React.JSX.Element {
  return (
    <div className="rounded-lg border border-border bg-muted/50 p-4 space-y-3">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <p className="text-sm" data-testid="session-current">
          <span className="text-muted-foreground">Session:</span>{" "}
          <span className="font-mono">{session.id}</span>
          {" | slug: "}
          <span className="font-mono">{session.slug}</span>
          {" | status: "}
          <Badge variant={statusVariant(session.status)}>{session.status}</Badge>
        </p>
        <GpuIndicator gpuId={session.gpu_id} status={session.status} />
      </div>
      <p className="font-mono text-sm" data-testid="session-slug">
        {session.slug}
      </p>
      <div className="grid grid-cols-1 gap-1 text-xs text-muted-foreground sm:grid-cols-3">
        <span>Created: {formatTimestamp(session.created_at)}</span>
        <span>Started: {formatTimestamp(session.started_at)}</span>
        <span>Stopped: {formatTimestamp(session.stopped_at)}</span>
      </div>
    </div>
  );
}

export { statusVariant };
