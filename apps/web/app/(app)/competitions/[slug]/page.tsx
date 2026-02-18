import { apiGet, type CompetitionDetail } from "@/lib/api";
import { buildMetricFields } from "@/lib/competition-fields";
import { inferServerSurface } from "@/lib/server-surface";
import { apiPathForSurface } from "@/lib/surface";
import { Separator } from "@/components/ui/separator";
import { MarkdownContent } from "@/components/shared/markdown-content";

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

  const fields = buildMetricFields(competition);

  return (
    <div className="space-y-8">
      <section>
        <MarkdownContent content={competition.description} />
      </section>

      <Separator />

      <section className="space-y-4">
        <h2 className="text-lg font-semibold tracking-tight">Competition Rules</h2>
        <dl className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {fields.map((field) => (
            <div key={field.label} className="space-y-1">
              <dt className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                {field.label}
              </dt>
              <dd className="font-mono text-sm">{field.value}</dd>
            </div>
          ))}
        </dl>
        <p className="text-xs text-muted-foreground">
          Spec version:{" "}
          <span className="font-mono">{competition.competition_spec_version}</span>
        </p>
      </section>
    </div>
  );
}
