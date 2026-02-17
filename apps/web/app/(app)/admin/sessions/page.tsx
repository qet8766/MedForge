import { HealthPanel } from "@/components/admin/health-panel";
import { SessionGrid } from "@/components/admin/session-grid";
import { PageHeader } from "@/components/layout/page-header";

export default function AdminSessionsPage(): React.JSX.Element {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Session Monitoring"
        description="Monitor active GPU sessions"
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <SessionGrid />
        <HealthPanel />
      </div>
    </div>
  );
}
