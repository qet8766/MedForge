import { BarChart3 } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

interface ScoreChartProps {
  slug: string;
}

export function ScoreChart({ slug: _slug }: ScoreChartProps): React.JSX.Element {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center gap-3 py-12 text-center">
        <div className="flex size-12 items-center justify-center rounded-full bg-muted">
          <BarChart3 className="size-6 text-muted-foreground" />
        </div>
        <div className="space-y-1">
          <p className="text-sm font-medium">Score progression chart coming soon</p>
          <p className="text-xs text-muted-foreground">
            Track how your scores improve over time.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
