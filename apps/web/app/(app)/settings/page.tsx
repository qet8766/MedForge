import type { Metadata } from "next";
import { Settings } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Settings - MedForge",
};

export default function SettingsPage(): React.JSX.Element {
  return (
    <div className="space-y-8">
      <PageHeader title="Settings" description="Account settings and preferences." />
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          <div className="flex size-12 items-center justify-center rounded-full bg-muted">
            <Settings className="size-6 text-muted-foreground" />
          </div>
          <p className="mt-4 text-sm font-medium">Settings features coming soon</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Account management and preferences will be available here.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
