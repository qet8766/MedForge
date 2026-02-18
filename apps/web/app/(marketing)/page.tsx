import Link from "next/link";
import { ArrowRight, Gpu, Trophy, BarChart3 } from "lucide-react";

import { apiGet, type CompetitionSummary } from "@/lib/api";
import { inferServerSurface } from "@/lib/server-surface";
import { apiPathForSurface } from "@/lib/surface";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export const dynamic = "force-dynamic";

const FEATURES = [
  {
    icon: Gpu,
    title: "GPU Sessions",
    description:
      "Launch GPU-accelerated SSH development environments on demand. Train models, run experiments, and iterate without managing infrastructure.",
  },
  {
    icon: Trophy,
    title: "Competitions",
    description:
      "Participate in structured machine learning competitions with standardized datasets, automated scoring, and reproducible benchmarks.",
  },
  {
    icon: BarChart3,
    title: "Leaderboards",
    description:
      "Track performance against peers with real-time leaderboards. Compare model metrics and submission histories across competitions.",
  },
] as const;

async function getCompetitionCount(): Promise<number> {
  try {
    const surface = await inferServerSurface();
    const path = apiPathForSurface(surface, "/competitions");
    const competitions = await apiGet<CompetitionSummary[]>(path);
    return competitions.length;
  } catch {
    return 0;
  }
}

export default async function LandingPage(): Promise<React.JSX.Element> {
  const competitionCount = await getCompetitionCount();

  return (
    <div className="animate-in">
      {/* Hero */}
      <section className="relative overflow-hidden px-6 py-24 sm:py-32">
        <div className="mx-auto max-w-4xl text-center">
          <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
            <span className="gradient-text">MedForge</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
            A GPU competition platform for research teams. Launch compute sessions,
            compete on standardized benchmarks, and push the state of the art.
          </p>
          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Button size="lg" asChild>
              <Link href="/auth/signup">
                Get started
                <ArrowRight className="ml-2 size-4" />
              </Link>
            </Button>
            <Button variant="outline" size="lg" asChild>
              <Link href="/competitions">
                Browse competitions
                {competitionCount > 0 ? (
                  <span className="ml-2 inline-flex size-5 items-center justify-center rounded-full bg-primary/10 text-xs font-medium text-primary">
                    {competitionCount}
                  </span>
                ) : null}
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-t px-6 py-20">
        <div className="mx-auto max-w-5xl">
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature) => {
              const Icon = feature.icon;
              return (
                <Card key={feature.title} className="border-border/50 bg-card/50">
                  <CardHeader className="space-y-3">
                    <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10">
                      <Icon className="size-5 text-primary" />
                    </div>
                    <CardTitle className="text-lg">{feature.title}</CardTitle>
                    <CardDescription className="leading-relaxed">
                      {feature.description}
                    </CardDescription>
                  </CardHeader>
                </Card>
              );
            })}
          </div>
        </div>
      </section>
    </div>
  );
}
