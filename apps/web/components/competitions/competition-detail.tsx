import type { CompetitionDetail } from "@/lib/api";
import { buildMetricFields } from "@/lib/competition-fields";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

type CompetitionDetailViewProps = {
  competition: CompetitionDetail;
};

export function CompetitionDetailView({ competition }: CompetitionDetailViewProps): React.JSX.Element {
  const fields = buildMetricFields(competition);

  return (
    <div className="space-y-8">
      <section className="space-y-4">
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight">{competition.title}</h1>
          <Badge variant={competition.competition_exposure === "internal" ? "outline" : "default"}>
            {competition.competition_exposure}
          </Badge>
          {competition.is_permanent ? (
            <Badge variant="secondary">Permanent</Badge>
          ) : null}
          <Badge variant="secondary">{competition.status}</Badge>
        </div>
        <p className="max-w-prose text-muted-foreground leading-relaxed">
          {competition.description}
        </p>
      </section>

      <Separator />

      <section className="space-y-4">
        <h2 className="text-lg font-semibold tracking-tight">Competition Details</h2>
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
      </section>

      <Separator />

      <section className="space-y-2">
        <h2 className="text-lg font-semibold tracking-tight">Spec</h2>
        <p className="text-xs text-muted-foreground">
          Competition spec version:{" "}
          <span className="font-mono">{competition.competition_spec_version}</span>
        </p>
      </section>
    </div>
  );
}
