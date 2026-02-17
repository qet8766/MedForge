import { Clock } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function SubmissionTimeline(): React.JSX.Element {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Submission History</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center gap-3 py-8 text-center">
          <Clock className="size-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Submission history will appear here.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
