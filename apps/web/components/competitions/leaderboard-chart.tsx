import { BarChart3 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function LeaderboardChart(): React.JSX.Element {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <BarChart3 className="size-4" />
          Score Distribution
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
          Score visualization coming soon.
        </div>
      </CardContent>
    </Card>
  );
}
