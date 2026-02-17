import { Download } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ExportDialog(): React.JSX.Element {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Export</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center gap-3 py-8 text-center">
          <Download className="size-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Export functionality coming soon.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
