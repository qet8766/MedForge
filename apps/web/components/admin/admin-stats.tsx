"use client";

import { useEffect, useState } from "react";

import { Activity, Monitor, Users } from "lucide-react";

import { apiGet, type HealthResponse, type SessionRead, type UserAdminRead } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type StatsState = {
  totalUsers: number | null;
  activeSessions: number | null;
  healthStatus: "ok" | "degraded" | "error" | null;
  loading: boolean;
};

function StatCard({
  title,
  value,
  icon,
  loading,
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
  loading: boolean;
}): React.JSX.Element {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-7 w-16" />
        ) : (
          <p className="text-2xl font-bold">{value}</p>
        )}
      </CardContent>
    </Card>
  );
}

export function AdminStats(): React.JSX.Element {
  const [stats, setStats] = useState<StatsState>({
    totalUsers: null,
    activeSessions: null,
    healthStatus: null,
    loading: true,
  });

  useEffect(() => {
    let cancelled = false;
    async function fetchStats(): Promise<void> {
      const results: Partial<StatsState> = {};

      try {
        const users = await apiGet<UserAdminRead[]>("/api/v2/admin/users");
        results.totalUsers = users.length;
      } catch {
        results.totalUsers = null;
      }

      try {
        const sessions = await apiGet<SessionRead[]>("/api/v2/admin/sessions");
        results.activeSessions = sessions.filter(
          (s) => s.status === "running" || s.status === "starting"
        ).length;
      } catch {
        results.activeSessions = null;
      }

      try {
        const health = await apiGet<HealthResponse>("/healthz");
        results.healthStatus = health.status;
      } catch {
        results.healthStatus = "error";
      }

      if (!cancelled) {
        setStats({
          totalUsers: results.totalUsers ?? null,
          activeSessions: results.activeSessions ?? null,
          healthStatus: results.healthStatus ?? null,
          loading: false,
        });
      }
    }
    void fetchStats();
    return () => { cancelled = true; };
  }, []);

  function formatHealthStatus(status: "ok" | "degraded" | "error" | null): string {
    if (status === null) return "--";
    if (status === "ok") return "Healthy";
    if (status === "degraded") return "Degraded";
    return "Error";
  }

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <StatCard
        title="Total Users"
        value={stats.totalUsers !== null ? String(stats.totalUsers) : "--"}
        icon={<Users className="size-4 text-muted-foreground" />}
        loading={stats.loading}
      />
      <StatCard
        title="Active Sessions"
        value={stats.activeSessions !== null ? String(stats.activeSessions) : "--"}
        icon={<Monitor className="size-4 text-muted-foreground" />}
        loading={stats.loading}
      />
      <StatCard
        title="System Health"
        value={formatHealthStatus(stats.healthStatus)}
        icon={<Activity className="size-4 text-muted-foreground" />}
        loading={stats.loading}
      />
    </div>
  );
}
