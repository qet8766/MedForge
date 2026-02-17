import Link from "next/link";
import { BarChart3, Monitor, Upload } from "lucide-react";

import { apiGet, type CompetitionDetail } from "@/lib/api";
import { inferServerSurface } from "@/lib/server-surface";
import { apiPathForSurface } from "@/lib/surface";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { CompetitionDetailView } from "@/components/competitions/competition-detail";

export const dynamic = "force-dynamic";

export default async function CompetitionDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<React.JSX.Element> {
  const { slug } = await params;
  const surface = await inferServerSurface();
  const competition = await apiGet<CompetitionDetail>(
    apiPathForSurface(surface, `/competitions/${slug}`),
  );

  return (
    <div className="container mx-auto space-y-8 px-4 py-8">
      <CompetitionDetailView competition={competition} />

      <Separator />

      <section className="flex flex-wrap gap-3">
        <Button asChild>
          <Link href={`/competitions/${slug}/leaderboard`}>
            <BarChart3 className="size-4" />
            Leaderboard
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href={`/competitions/${slug}/submit`}>
            <Upload className="size-4" />
            Submit
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href="/sessions">
            <Monitor className="size-4" />
            Sessions
          </Link>
        </Button>
      </section>
    </div>
  );
}
