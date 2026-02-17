import { ScoringQueue } from "@/components/admin/scoring-queue";
import { PageHeader } from "@/components/layout/page-header";

export default function AdminCompetitionsPage(): React.JSX.Element {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Competition Management"
        description="Manage competitions and scoring"
      />

      <ScoringQueue />
    </div>
  );
}
