import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/layout/page-header";
import { ProfileHeader } from "@/components/profile/profile-header";
import { SubmissionTimeline } from "@/components/profile/submission-timeline";
import { ExportDialog } from "@/components/profile/export-dialog";

export default async function ProfilePage({
  params,
}: {
  params: Promise<{ handle: string }>;
}): Promise<React.JSX.Element> {
  const { handle } = await params;

  return (
    <div className="space-y-6">
      <PageHeader title="Member Profile" description={`Viewing profile for ${handle}`} />

      <Card>
        <CardContent className="pt-6">
          <ProfileHeader handle={handle} />
          <p className="mt-4 text-sm text-muted-foreground">
            Activity and submission history will be displayed here in a future update.
          </p>
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        <SubmissionTimeline />
        <ExportDialog />
      </div>
    </div>
  );
}
