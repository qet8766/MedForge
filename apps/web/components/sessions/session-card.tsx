import Link from "next/link";

import { ExternalLink } from "lucide-react";

import type { SessionRead } from "@/lib/contracts";
import { formatTimestamp } from "@/lib/format";
import { sessionUrl } from "@/lib/surface";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/status-badge";
import { GpuIndicator } from "@/components/sessions/gpu-indicator";

type SessionCardProps = {
  session: SessionRead;
};

export function SessionCard({ session }: SessionCardProps): React.JSX.Element {
  const isRunning = session.status === "running";
  const ideUrl = sessionUrl(session.slug);

  return (
    <Card data-testid="session-current">
      <CardHeader>
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <Link
              href={`/sessions/${session.id}`}
              className="hover:underline"
            >
              <CardTitle className="font-mono">{session.slug}</CardTitle>
            </Link>
            <StatusBadge status={session.status} />
          </div>
          <GpuIndicator gpuId={session.gpu_id} status={session.status} />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-1 gap-1 text-xs text-muted-foreground sm:grid-cols-3">
          <span>Created: {formatTimestamp(session.created_at)}</span>
          <span>Started: {formatTimestamp(session.started_at)}</span>
          <span>Stopped: {formatTimestamp(session.stopped_at)}</span>
        </div>

        {isRunning ? (
          <div className="flex gap-2">
            <Button size="sm" asChild>
              <a href={ideUrl} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="size-4" />
                Open IDE
              </a>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link href={`/sessions/${session.id}`}>
                Details
              </Link>
            </Button>
          </div>
        ) : (
          <Button variant="outline" size="sm" asChild>
            <Link href={`/sessions/${session.id}`}>
              View Details
            </Link>
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
