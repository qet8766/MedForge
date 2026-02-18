import { AdminStats } from "@/components/admin/admin-stats";
import { HealthPanel } from "@/components/admin/health-panel";
import { SessionGrid } from "@/components/admin/session-grid";
import { PageHeader } from "@/components/layout/page-header";

export default function AdminSessionsPage(): React.JSX.Element {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Session Monitoring"
        description="Monitor active GPU sessions and system health"
      />

      <AdminStats />

      <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
        <SessionGrid />
        <HealthPanel />
      </div>
    </div>
  );
}
