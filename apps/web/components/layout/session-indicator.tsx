"use client";

import Link from "next/link";
import { Copy, Plus, Monitor } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import { useSessionContext } from "@/components/providers/session-provider";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

type SessionIndicatorProps = {
  collapsed?: boolean;
};

export function SessionIndicator({ collapsed = false }: SessionIndicatorProps): React.JSX.Element {
  const { session, loading } = useSessionContext();

  if (loading) {
    return (
      <div className={cn("border-b p-3", collapsed && "flex justify-center p-2")}>
        {collapsed ? (
          <Skeleton className="size-8 rounded-md" />
        ) : (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-6 w-full" />
          </div>
        )}
      </div>
    );
  }

  if (collapsed) {
    return (
      <div className="flex justify-center border-b p-2">
        <Button
          variant={session ? "secondary" : "ghost"}
          size="icon-sm"
          asChild
        >
          <Link href={session ? "/sessions" : "/sessions"}>
            <Monitor className={cn("size-4", session && "text-primary")} />
            <span className="sr-only">
              {session ? `Session ${session.slug}` : "No active session"}
            </span>
          </Link>
        </Button>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="border-b p-3">
        <p className="mb-2 text-xs text-muted-foreground">No active session</p>
        <Button variant="outline" size="sm" className="w-full gap-1.5" asChild>
          <Link href="/sessions">
            <Plus className="size-3.5" />
            New Session
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="border-b p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="truncate text-xs font-medium text-muted-foreground">
          Session
        </p>
        <StatusBadge status={session.status} className="text-[10px] px-1.5 py-0" />
      </div>
      <p className="mt-1 truncate font-mono text-sm">{session.slug}</p>
      {session.status === "running" && session.ssh_port > 0 && (
        <Button
          variant="outline"
          size="sm"
          className="mt-2 w-full gap-1.5"
          onClick={() => {
            const cmd = `ssh coder@${session.ssh_host} -p ${session.ssh_port}`;
            void navigator.clipboard.writeText(cmd);
            toast.success("SSH command copied to clipboard.");
          }}
        >
          <Copy className="size-3.5" />
          Copy SSH
        </Button>
      )}
    </div>
  );
}
