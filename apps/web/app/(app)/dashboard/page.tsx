import { Trophy, Monitor } from "lucide-react";

import { apiGet, type CompetitionSummary, type MeResponse, type SessionCurrentResponse } from "@/lib/api";
import { inferServerSurface } from "@/lib/server-surface";
import { apiPathForSurface } from "@/lib/surface";
import { PageHeader } from "@/components/layout/page-header";
import { StatsCard } from "@/components/dashboard/stats-card";
import { QuickActions } from "@/components/dashboard/quick-actions";
import { SessionSummary } from "@/components/dashboard/session-summary";

export const dynamic = "force-dynamic";

export default async function DashboardPage(): Promise<React.JSX.Element> {
  const surface = await inferServerSurface();

  const [competitions, sessionResponse, me] = await Promise.all([
    apiGet<CompetitionSummary[]>(apiPathForSurface(surface, "/competitions")).catch(
      (): CompetitionSummary[] => []
    ),
    apiGet<SessionCurrentResponse>(apiPathForSurface(surface, "/sessions/current")).catch(
      (): null => null
    ),
    apiGet<MeResponse>("/api/v2/me").catch((): null => null),
  ]);

  const activeSession = sessionResponse?.session ?? null;
  const greeting = me?.email ? `Welcome back, ${me.email}` : "Welcome back";

  return (
    <div className="space-y-8">
      <PageHeader title={greeting} description="Here is an overview of your MedForge workspace." />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatsCard
          title="Competitions"
          value={competitions.length}
          description="Available challenges"
          icon={<Trophy className="size-5" />}
        />
        <StatsCard
          title="Session Status"
          value={activeSession ? activeSession.status : "None"}
          description={activeSession ? `Slug: ${activeSession.slug}` : "No active session"}
          icon={<Monitor className="size-5" />}
        />
      </div>

      {activeSession ? <SessionSummary session={activeSession} /> : null}

      <section className="space-y-4">
        <h2 className="text-lg font-semibold tracking-tight">Quick Actions</h2>
        <QuickActions />
      </section>
    </div>
  );
}
