import { Monitor } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function SessionGrid(): React.JSX.Element {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Active Sessions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center gap-3 py-8 text-center">
          <Monitor className="size-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Session monitoring coming soon.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
