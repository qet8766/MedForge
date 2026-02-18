"use client";

import { useCallback, useEffect, useState } from "react";

import { Monitor } from "lucide-react";

import { apiGet, type SessionRead, type SessionStatus } from "@/lib/api";
import { formatRelativeTime, getErrorMessage } from "@/lib/format";
import { useFetchState } from "@/lib/hooks/use-fetch-state";
import { usePolling } from "@/lib/hooks/use-polling";
import { StatusBadge } from "@/components/shared/status-badge";
import { TableErrorState } from "@/components/shared/table-states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

const ALL_STATUSES: SessionStatus[] = ["starting", "running", "stopping", "stopped", "error"];

const AUTO_REFRESH_MS = 10_000;

function SessionCardSkeleton(): React.JSX.Element {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-4 w-24" />
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-3 w-28" />
        </div>
      </CardContent>
    </Card>
  );
}

function SessionCard({ session }: { session: SessionRead }): React.JSX.Element {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-mono">{session.slug}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Status</span>
            <StatusBadge status={session.status} variant="session" />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">GPU</span>
            <span>{session.gpu_id}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Exposure</span>
            <Badge variant="outline">{session.exposure}</Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">User</span>
            <span className="truncate max-w-[140px] text-xs font-mono" title={session.user_id}>
              {session.user_id.slice(0, 8)}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Created</span>
            <span className="text-muted-foreground">{formatRelativeTime(session.created_at)}</span>
          </div>
          {session.error_message !== null && (
            <p className="text-xs text-destructive mt-1">{session.error_message}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function SessionGrid(): React.JSX.Element {
  const [state, setState] = useFetchState<SessionRead[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const fetchSessions = useCallback(async (): Promise<void> => {
    try {
      const sessions = await apiGet<SessionRead[]>("/api/v2/admin/sessions");
      setState({ data: sessions, loading: false, error: null });
    } catch (err) {
      const message = getErrorMessage(err, "Failed to load sessions.");
      setState((prev) => ({ ...prev, loading: false, error: message }));
    }
  }, [setState]);

  useEffect(() => {
    void fetchSessions();
  }, [fetchSessions]);

  const hasActive = state.data.some(
    (s) => s.status === "starting" || s.status === "running" || s.status === "stopping"
  );

  usePolling(() => { void fetchSessions(); }, AUTO_REFRESH_MS, hasActive);

  const filteredSessions = statusFilter === "all"
    ? state.data
    : state.data.filter((s) => s.status === statusFilter);

  if (state.loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-96" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <SessionCardSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (state.error !== null) {
    return <TableErrorState message={state.error} />;
  }

  return (
    <div className="space-y-4">
      <ToggleGroup
        type="single"
        value={statusFilter}
        onValueChange={(value) => {
          if (value) setStatusFilter(value);
        }}
        variant="outline"
        size="sm"
      >
        <ToggleGroupItem value="all">
          All ({state.data.length})
        </ToggleGroupItem>
        {ALL_STATUSES.map((s) => {
          const count = state.data.filter((sess) => sess.status === s).length;
          return (
            <ToggleGroupItem key={s} value={s}>
              {s} ({count})
            </ToggleGroupItem>
          );
        })}
      </ToggleGroup>

      {filteredSessions.length === 0 ? (
        <Card>
          <CardContent>
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <Monitor className="size-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                No sessions match the current filter.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredSessions.map((session) => (
            <SessionCard key={session.id} session={session} />
          ))}
        </div>
      )}
    </div>
  );
}
