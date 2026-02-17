import { FolderOpen } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function DatasetExplorer(): React.JSX.Element {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">File Explorer</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center gap-3 py-8 text-center">
          <FolderOpen className="size-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Dataset file explorer coming soon.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
