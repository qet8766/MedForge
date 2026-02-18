"use client";

import Link from "next/link";

import {
  AlertTriangle,
  ArrowLeft,
  Copy,
  Square,
  Terminal,
} from "lucide-react";
import { toast } from "sonner";

import type { SessionRead } from "@/lib/contracts";
import { formatTimestamp } from "@/lib/format";
import { isTransitioning } from "@/lib/status";
import { useAuthContext } from "@/components/providers/auth-provider";
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
  const { user } = useAuthContext();
  const isActive =
    session.status === "running" || session.status === "starting";
  const sshCommand = `ssh coder@${session.ssh_host} -p ${session.ssh_port}`;
  const vscodeUri = `vscode://vscode-remote/ssh-remote+coder@${session.ssh_host}:${session.ssh_port}/workspace`;
  const hasNoSshKey = !user?.ssh_public_key;

  function handleCopySshCommand(): void {
    void navigator.clipboard.writeText(sshCommand);
    toast.success("SSH command copied to clipboard.");
  }

  function handleOpenVSCode(): void {
    window.open(vscodeUri, "_self");
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

      {isActive && hasNoSshKey ? (
        <div className="rounded-lg border border-yellow-500/50 bg-yellow-500/10 p-4 flex items-start gap-3">
          <AlertTriangle className="size-5 text-yellow-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-yellow-700">No SSH key configured</p>
            <p className="text-sm text-yellow-600 mt-1">
              Add your SSH public key in{" "}
              <Link href="/settings/profile" className="underline underline-offset-4 hover:text-yellow-700">
                Settings
              </Link>{" "}
              to connect to this session.
            </p>
          </div>
        </div>
      ) : null}

      {isActive && session.ssh_port > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Terminal className="size-4" />
              SSH Connection
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2 rounded-md bg-muted px-3 py-2 font-mono text-sm">
              <span className="flex-1 truncate">{sshCommand}</span>
              <Button variant="ghost" size="icon" className="shrink-0 size-7" onClick={handleCopySshCommand}>
                <Copy className="size-3.5" />
              </Button>
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={handleCopySshCommand}>
                <Copy className="size-4" />
                Copy SSH Command
              </Button>
              <Button variant="outline" size="sm" onClick={handleOpenVSCode}>
                <Terminal className="size-4" />
                Open in VS Code
              </Button>
            </div>
          </CardContent>
        </Card>
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
              {session.ssh_port > 0 ? (
                <MetadataRow label="SSH Port">
                  {session.ssh_port}
                </MetadataRow>
              ) : null}
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
        {isActive && onStop ? (
          <ConfirmDialog
            title="Stop Session"
            description={`This will stop session ${session.slug}. Any unsaved work may be lost.`}
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
