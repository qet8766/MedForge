import { Badge } from "@/components/ui/badge";

type MetricBadgeProps = {
  label: string;
  value: string;
};

export function MetricBadge({ label, value }: MetricBadgeProps): React.JSX.Element {
  return (
    <Badge variant="secondary" className="gap-1.5">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono">{value}</span>
    </Badge>
  );
}
