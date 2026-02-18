export function rankBackground(rank: number): string | undefined {
  switch (rank) {
    case 1:
      return "bg-yellow-500/10";
    case 2:
      return "bg-zinc-400/10";
    case 3:
      return "bg-amber-700/10";
    default:
      return undefined;
  }
}

export function rankLabel(rank: number): string {
  switch (rank) {
    case 1:
      return "\ud83e\udd47";
    case 2:
      return "\ud83e\udd48";
    case 3:
      return "\ud83e\udd49";
    default:
      return String(rank);
  }
}

export function formatScoredAt(scoredAt: string | null): string {
  if (scoredAt === null) {
    return "pending";
  }
  return new Date(scoredAt).toLocaleString();
}
