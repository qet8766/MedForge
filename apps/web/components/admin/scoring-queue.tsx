"use client";

import { useCallback, useEffect } from "react";

import { apiGet, type CompetitionSummary, type SubmissionRead } from "@/lib/api";
import { formatRelativeTime, getErrorMessage } from "@/lib/format";
import { useFetchState } from "@/lib/hooks/use-fetch-state";
import { TableEmptyState, TableErrorState } from "@/components/shared/table-states";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type PendingSubmission = SubmissionRead & {
  competition_title: string;
};


function ScoringQueueSkeleton(): React.JSX.Element {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Scoring Queue</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      </CardContent>
    </Card>
  );
}

export function ScoringQueue(): React.JSX.Element {
  const [state, setState] = useFetchState<PendingSubmission[]>([]);

  const fetchPendingSubmissions = useCallback(async (): Promise<void> => {
    try {
      const competitions = await apiGet<CompetitionSummary[]>("/api/v2/external/competitions");
      const allPending: PendingSubmission[] = [];

      for (const comp of competitions) {
        try {
          const submissions = await apiGet<SubmissionRead[]>(
            `/api/v2/external/competitions/${comp.slug}/submissions/me`
          );
          const pending = submissions
            .filter((s) => s.score_status === "queued" || s.score_status === "scoring")
            .map((s) => ({ ...s, competition_title: comp.title }));
          allPending.push(...pending);
        } catch {
          // User may not have submissions for this competition
        }
      }

      allPending.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      setState({ data: allPending, loading: false, error: null });
    } catch (err) {
      const message = getErrorMessage(err, "Failed to load scoring queue.");
      setState({ data: [], loading: false, error: message });
    }
  }, [setState]);

  useEffect(() => {
    void fetchPendingSubmissions();
  }, [fetchPendingSubmissions]);

  if (state.loading) {
    return <ScoringQueueSkeleton />;
  }

  if (state.error !== null) {
    return <TableErrorState message={state.error} />;
  }

  if (state.data.length === 0) {
    return <TableEmptyState message="No pending submissions in the scoring queue." />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          Scoring Queue ({state.data.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Competition</TableHead>
              <TableHead>Filename</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Submitted</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {state.data.map((sub) => (
              <TableRow key={sub.id}>
                <TableCell className="font-medium">{sub.competition_title}</TableCell>
                <TableCell className="text-muted-foreground text-xs font-mono">
                  {sub.filename}
                </TableCell>
                <TableCell>
                  <StatusBadge status={sub.score_status} variant="score" />
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {formatRelativeTime(sub.created_at)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
