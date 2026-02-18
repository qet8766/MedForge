import { cn } from "@/lib/utils";

type MetricDisplayProps = {
  label: string;
  value: string | number;
  description?: string;
  className?: string;
};

export function MetricDisplay({ label, value, description, className }: MetricDisplayProps): React.JSX.Element {
  return (
    <div className={cn("space-y-1", className)}>
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="text-2xl font-bold tracking-tight">{value}</p>
      {description ? (
        <p className="text-xs text-muted-foreground">{description}</p>
      ) : null}
    </div>
  );
}
