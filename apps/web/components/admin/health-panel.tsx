"use client";

import { useEffect, useState } from "react";

import { Activity } from "lucide-react";

import { apiGet, type HealthResponse } from "@/lib/api";
import { getErrorMessage } from "@/lib/format";
import { usePolling } from "@/lib/hooks/use-polling";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const AUTO_REFRESH_MS = 30_000;

type HealthState = {
  health: HealthResponse | null;
  loading: boolean;
  error: string | null;
  lastChecked: Date | null;
};

function HealthPanelSkeleton(): React.JSX.Element {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">System Health</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center gap-3 py-4">
          <Skeleton className="size-10 rounded-full" />
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-3 w-32" />
        </div>
      </CardContent>
    </Card>
  );
}

function statusColor(status: "ok" | "degraded"): string {
  if (status === "ok") return "bg-green-500";
  return "bg-yellow-500";
}

function statusBadgeVariant(status: "ok" | "degraded"): "default" | "outline" {
  if (status === "ok") return "default";
  return "outline";
}

export function HealthPanel(): React.JSX.Element {
  const [state, setState] = useState<HealthState>({
    health: null,
    loading: true,
    error: null,
    lastChecked: null,
  });

  useEffect(() => {
    let cancelled = false;
    async function doFetch(): Promise<void> {
      try {
        const health = await apiGet<HealthResponse>("/healthz");
        if (!cancelled) {
          setState({
            health,
            loading: false,
            error: null,
            lastChecked: new Date(),
          });
        }
      } catch (err) {
        const message = getErrorMessage(err, "Failed to check health.");
        if (!cancelled) {
          setState((prev) => ({
            ...prev,
            loading: false,
            error: message,
            lastChecked: new Date(),
          }));
        }
      }
    }
    void doFetch();
    return () => { cancelled = true; };
  }, []);

  usePolling(() => {
    async function poll(): Promise<void> {
      try {
        const health = await apiGet<HealthResponse>("/healthz");
        setState({
          health,
          loading: false,
          error: null,
          lastChecked: new Date(),
        });
      } catch (err) {
        const message = getErrorMessage(err, "Failed to check health.");
        setState((prev) => ({
          ...prev,
          loading: false,
          error: message,
          lastChecked: new Date(),
        }));
      }
    }
    void poll();
  }, AUTO_REFRESH_MS, true);

  if (state.loading) {
    return <HealthPanelSkeleton />;
  }

  if (state.error !== null) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">System Health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-3 py-4 text-center">
            <Activity className="size-8 text-destructive" />
            <p className="text-sm text-destructive">{state.error}</p>
            {state.lastChecked !== null && (
              <p className="text-xs text-muted-foreground">
                Last checked: {state.lastChecked.toLocaleTimeString()}
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (state.health === null) {
    return <HealthPanelSkeleton />;
  }

  const status = state.health.status;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">System Health</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center gap-3 py-4">
          <div className="relative flex items-center justify-center">
            <span className={`size-3 rounded-full ${statusColor(status)}`} />
            {status === "ok" && (
              <span className={`absolute size-3 rounded-full ${statusColor(status)} animate-ping`} />
            )}
          </div>
          <Badge variant={statusBadgeVariant(status)}>
            {status === "ok" ? "Healthy" : "Degraded"}
          </Badge>
          {state.lastChecked !== null && (
            <p className="text-xs text-muted-foreground">
              Last checked: {state.lastChecked.toLocaleTimeString()}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
