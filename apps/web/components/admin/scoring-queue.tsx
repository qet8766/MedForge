import { ListOrdered } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ScoringQueue(): React.JSX.Element {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Scoring Queue</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center gap-3 py-8 text-center">
          <ListOrdered className="size-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Scoring queue coming soon.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
