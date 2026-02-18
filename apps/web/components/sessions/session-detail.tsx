"use client";

import Link from "next/link";

import {
  ArrowLeft,
  Copy,
  ExternalLink,
  Square,
} from "lucide-react";
import { toast } from "sonner";

import type { SessionRead } from "@/lib/contracts";
import { formatTimestamp } from "@/lib/format";
import { isTransitioning } from "@/lib/status";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/status-badge";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { GpuIndicator } from "@/components/sessions/gpu-indicator";
import { SessionTimeline } from "@/components/sessions/session-timeline";

type MetadataRowProps = {
  label: string;
  children: React.ReactNode;
};

function MetadataRow({ label, children }: MetadataRowProps): React.JSX.Element {
  return (
    <div className="flex items-start justify-between gap-4 py-2 border-b border-border/50 last:border-0">
      <span className="text-sm text-muted-foreground shrink-0">{label}</span>
      <span className="text-sm font-mono text-right break-all">{children}</span>
    </div>
  );
}

type SessionDetailProps = {
  session: SessionRead;
  onStop?: () => Promise<void>;
};

export function SessionDetail({
  session,
  onStop,
}: SessionDetailProps): React.JSX.Element {
  const isActive =
    session.status === "running" || session.status === "starting";
  const sessionUrl = `https://${session.slug}.sessions.medforge.dev`;

  function handleCopyUrl(): void {
    void navigator.clipboard.writeText(sessionUrl);
    toast.success("Session URL copied to clipboard.");
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/sessions">
            <ArrowLeft className="size-4" />
          </Link>
        </Button>
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <h1 className="text-2xl font-bold tracking-tight font-mono truncate">
            {session.slug}
          </h1>
          <StatusBadge status={session.status} className="text-sm" />
        </div>
      </div>

      {session.error_message ? (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm font-medium text-destructive">Error</p>
          <p className="text-sm text-destructive/80 mt-1">
            {session.error_message}
          </p>
        </div>
      ) : null}

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Timeline</CardTitle>
          </CardHeader>
          <CardContent>
            <SessionTimeline session={session} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div>
              <MetadataRow label="Session ID">
                {session.id}
              </MetadataRow>
              <MetadataRow label="GPU">
                <GpuIndicator gpuId={session.gpu_id} status={session.status} />
              </MetadataRow>
              <MetadataRow label="Exposure">
                {session.exposure.toUpperCase()}
              </MetadataRow>
              <MetadataRow label="Pack">
                {session.pack_id}
              </MetadataRow>
              <MetadataRow label="Workspace">
                {session.workspace_zfs}
              </MetadataRow>
              {session.container_id ? (
                <MetadataRow label="Container">
                  {session.container_id.slice(0, 12)}
                </MetadataRow>
              ) : null}
              <MetadataRow label="Created">
                {formatTimestamp(session.created_at)}
              </MetadataRow>
              <MetadataRow label="Started">
                {formatTimestamp(session.started_at)}
              </MetadataRow>
              <MetadataRow label="Stopped">
                {formatTimestamp(session.stopped_at)}
              </MetadataRow>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex flex-wrap gap-3">
        {isActive ? (
          <Button asChild>
            <a href={sessionUrl} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="size-4" />
              Open IDE
            </a>
          </Button>
        ) : null}

        <Button variant="outline" onClick={handleCopyUrl}>
          <Copy className="size-4" />
          Copy URL
        </Button>

        {isActive && onStop ? (
          <ConfirmDialog
            title="Stop Session"
            description={`This will stop session ${session.slug}. Any unsaved work in the IDE may be lost.`}
            confirmLabel="Stop Session"
            onConfirm={onStop}
            trigger={
              <Button
                variant="destructive"
                disabled={isTransitioning(session.status)}
                data-testid="session-stop"
              >
                <Square className="size-4" />
                Stop Session
              </Button>
            }
          />
        ) : null}
      </div>
    </div>
  );
}
