import { Activity } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function HealthPanel(): React.JSX.Element {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">System Health</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center gap-3 py-8 text-center">
          <Activity className="size-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Health status indicators coming soon.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
