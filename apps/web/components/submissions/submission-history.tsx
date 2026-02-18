"use client";

import { useCallback, useEffect } from "react";
import { Loader2 } from "lucide-react";

import { apiGet, type SubmissionRead } from "@/lib/api";
import { formatRelativeTime, formatScore, getErrorMessage } from "@/lib/format";
import { useFetchState } from "@/lib/hooks/use-fetch-state";
import { apiPathForSurface, inferClientSurface } from "@/lib/surface";
import { TableEmptyState, TableErrorState } from "@/components/shared/table-states";
import { StatusBadge } from "@/components/shared/status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type SubmissionHistoryProps = {
  slug: string;
  onSubmissionsLoaded?: (submissions: SubmissionRead[]) => void;
};

export function SubmissionHistory({ slug, onSubmissionsLoaded }: SubmissionHistoryProps): React.JSX.Element {
  const [state, setState] = useFetchState<SubmissionRead[]>([]);

  const fetchSubmissions = useCallback(async (): Promise<void> => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    const surface = inferClientSurface();
    const path = apiPathForSurface(surface, `/competitions/${slug}/submissions/me`);
    try {
      const data = await apiGet<SubmissionRead[]>(path);
      setState({ data, loading: false, error: null });
      onSubmissionsLoaded?.(data);
    } catch (fetchError) {
      const message = getErrorMessage(fetchError, "Failed to load submissions");
      setState((prev) => ({ ...prev, loading: false, error: message }));
    }
  }, [slug, onSubmissionsLoaded, setState]);

  useEffect(() => {
    void fetchSubmissions();
  }, [fetchSubmissions]);

  if (state.loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="size-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (state.error !== null) {
    return <TableErrorState message={state.error} />;
  }

  if (state.data.length === 0) {
    return <TableEmptyState message="No submissions yet. Submit a CSV file to see your results here." />;
  }

  return (
    <div className="space-y-4">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Filename</TableHead>
            <TableHead>Score</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Submitted At</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {state.data.map((submission) => (
            <TableRow key={submission.id}>
              <TableCell className="font-mono text-sm">{submission.filename}</TableCell>
              <TableCell className="font-mono tabular-nums">
                {submission.official_score
                  ? formatScore(submission.official_score.primary_score)
                  : "--"}
              </TableCell>
              <TableCell>
                <StatusBadge status={submission.score_status} variant="score" />
              </TableCell>
              <TableCell className="text-right text-sm text-muted-foreground">
                {formatRelativeTime(submission.created_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
