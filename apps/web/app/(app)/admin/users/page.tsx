import { Card, CardContent } from "@/components/ui/card";
import { UserTable } from "@/components/admin/user-table";
import { PageHeader } from "@/components/layout/page-header";

export default function AdminUsersPage(): React.JSX.Element {
  return (
    <div className="space-y-6">
      <PageHeader
        title="User Management"
        description="View and manage platform users"
      />

      <Card>
        <CardContent className="pt-6">
          <UserTable />
        </CardContent>
      </Card>
    </div>
  );
}
