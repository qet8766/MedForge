"use client";

import { useCallback, useEffect, useState } from "react";

import { Monitor } from "lucide-react";
import { toast } from "sonner";

import {
  apiGet,
  type SessionListItem,
} from "@/lib/api";
import { formatRelativeTime, formatTimestamp } from "@/lib/format";
import { apiPathForSurface, inferClientSurface } from "@/lib/surface";
import { useSessionContext } from "@/components/providers/session-provider";
import { SessionCard } from "@/components/sessions/session-card";
import { SessionControls } from "@/components/sessions/session-controls";
import { StatusBadge } from "@/components/shared/status-badge";
import { DataTable, type DataTableColumn } from "@/components/shared/data-table";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

type SessionsApiResponse = SessionListItem[];

const STATUS_FILTERS = ["all", "running", "starting", "stopped", "stopping", "error"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

const SESSION_COLUMNS: DataTableColumn<SessionListItem>[] = [
  {
    key: "slug",
    header: "Slug",
    render: (row) => (
      <a
        href={`/sessions/${row.id}`}
        className="font-mono text-primary hover:underline"
      >
        {row.slug}
      </a>
    ),
  },
  {
    key: "status",
    header: "Status",
    render: (row) => <StatusBadge status={row.status} />,
  },
  {
    key: "gpu",
    header: "GPU",
    render: (row) => <span className="font-mono">{row.gpu_id}</span>,
  },
  {
    key: "exposure",
    header: "Exposure",
    render: (row) => (
      <span className="text-xs uppercase">{row.exposure}</span>
    ),
  },
  {
    key: "created",
    header: "Created",
    render: (row) => (
      <span title={formatTimestamp(row.created_at)}>
        {formatRelativeTime(row.created_at)}
      </span>
    ),
  },
  {
    key: "started",
    header: "Started",
    render: (row) => formatTimestamp(row.started_at),
  },
  {
    key: "stopped",
    header: "Stopped",
    render: (row) => formatTimestamp(row.stopped_at),
  },
];

export default function SessionsPage(): React.JSX.Element {
  const { session: activeSession, stopSession, refresh } = useSessionContext();
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const surface = inferClientSurface();

  const fetchSessions = useCallback(async (): Promise<void> => {
    setLoading(true);
    try {
      const queryParams =
        statusFilter === "all" ? "" : `?status=${statusFilter}`;
      const response = await apiGet<SessionsApiResponse>(
        apiPathForSurface(surface, `/sessions${queryParams}`)
      );
      setSessions(response);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load sessions.";
      toast.error(message);
      setSessions([]);
    } finally {
      setLoading(false);
    }
  }, [surface, statusFilter]);

  useEffect(() => {
    void fetchSessions();
  }, [fetchSessions]);

  async function handleStopSession(): Promise<void> {
    await stopSession();
    toast.success("Session stop requested.");
    refresh();
    await fetchSessions();
  }

  function handleSessionCreated(): void {
    refresh();
    void fetchSessions();
  }

  const filteredSessions =
    statusFilter === "all"
      ? sessions
      : sessions.filter((s) => s.status === statusFilter);

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Monitor className="size-6" />
            Sessions
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage your GPU-backed development sessions.
          </p>
        </div>
        <SessionControls
          hasActiveSession={activeSession !== null}
          activeSessionSlug={activeSession?.slug ?? null}
          activeSessionStatus={activeSession?.status ?? null}
          onStopSession={handleStopSession}
          onSessionCreated={handleSessionCreated}
        />
      </div>

      {activeSession ? (
        <section>
          <h2 className="text-lg font-semibold mb-3">Active Session</h2>
          <SessionCard session={activeSession} />
        </section>
      ) : null}

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <h2 className="text-lg font-semibold">Session History</h2>
          <ToggleGroup
            type="single"
            variant="outline"
            value={statusFilter}
            onValueChange={(value) => {
              if (value) {
                setStatusFilter(value as StatusFilter);
              }
            }}
          >
            {STATUS_FILTERS.map((filter) => (
              <ToggleGroupItem key={filter} value={filter} className="text-xs capitalize">
                {filter}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </div>

        <DataTable<SessionListItem>
          columns={SESSION_COLUMNS}
          data={filteredSessions}
          loading={loading}
          emptyMessage="No sessions found."
          pageSize={20}
          keyExtractor={(row) => row.id}
        />
      </section>
    </div>
  );
}
