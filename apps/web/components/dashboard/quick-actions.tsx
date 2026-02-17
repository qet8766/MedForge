import Link from "next/link";
import { Database, Monitor, Trophy } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

const ACTIONS = [
  {
    href: "/sessions",
    label: "Create Session",
    description: "Launch a GPU-powered workspace",
    icon: Monitor,
  },
  {
    href: "/competitions",
    label: "Browse Competitions",
    description: "Explore active challenges",
    icon: Trophy,
  },
  {
    href: "/datasets",
    label: "View Datasets",
    description: "Browse available data",
    icon: Database,
  },
] as const;

export function QuickActions(): React.JSX.Element {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {ACTIONS.map((action) => {
        const Icon = action.icon;
        return (
          <Link key={action.href} href={action.href} className="group">
            <Card className="transition-colors group-hover:border-primary/40">
              <CardContent className="flex items-center gap-4">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Icon className="size-5" />
                </div>
                <div className="space-y-0.5">
                  <p className="text-sm font-semibold">{action.label}</p>
                  <p className="text-xs text-muted-foreground">{action.description}</p>
                </div>
              </CardContent>
            </Card>
          </Link>
        );
      })}
    </div>
  );
}
