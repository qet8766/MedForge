import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { sessionStatusVariant, scoreStatusVariant, isTransitioning } from "@/lib/status";

type StatusBadgeProps = {
  status: string;
  variant?: "session" | "score";
  className?: string;
};

export function StatusBadge({ status, variant = "session", className }: StatusBadgeProps): React.JSX.Element {
  const badgeVariant = variant === "session"
    ? sessionStatusVariant(status)
    : scoreStatusVariant(status);

  return (
    <Badge
      variant={badgeVariant}
      className={cn(
        isTransitioning(status) && "animate-pulse",
        className
      )}
    >
      {status}
    </Badge>
  );
}
