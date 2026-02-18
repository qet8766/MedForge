type BadgeVariant = "default" | "secondary" | "destructive" | "outline"

export function sessionStatusVariant(status: string): BadgeVariant {
  switch (status) {
    case "running":
      return "default"
    case "starting":
      return "outline"
    case "stopped":
    case "stopping":
      return "secondary"
    case "error":
      return "destructive"
    default:
      return "outline"
  }
}

export function scoreStatusVariant(status: string): BadgeVariant {
  switch (status) {
    case "scored":
      return "default"
    case "scoring":
      return "outline"
    case "queued":
      return "secondary"
    case "failed":
      return "destructive"
    default:
      return "outline"
  }
}

export function isTransitioning(status: string): boolean {
  return status === "starting" || status === "stopping"
}
