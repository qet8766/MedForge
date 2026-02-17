import Link from "next/link";
import { Monitor } from "lucide-react";

import type { SessionRead, SessionStatus } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function statusVariant(status: SessionStatus): "default" | "outline" | "secondary" | "destructive" {
  switch (status) {
    case "running":
      return "default";
    case "starting":
      return "outline";
    case "stopped":
    case "stopping":
      return "secondary";
    case "error":
      return "destructive";
  }
}

interface SessionSummaryProps {
  session: SessionRead;
}

export function SessionSummary({ session }: SessionSummaryProps): React.JSX.Element {
  return (
    <Link href="/sessions" className="group block">
      <Card className="transition-colors group-hover:border-primary/40">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Monitor className="size-4 text-primary" />
            Active Session
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
          <div>
            <span className="text-muted-foreground">Slug: </span>
            <span className="font-mono font-medium">{session.slug}</span>
          </div>
          <div>
            <span className="text-muted-foreground">GPU: </span>
            <span className="font-medium">{session.gpu_id}</span>
          </div>
          <Badge variant={statusVariant(session.status)}>
            {session.status}
          </Badge>
        </CardContent>
      </Card>
    </Link>
  );
}
