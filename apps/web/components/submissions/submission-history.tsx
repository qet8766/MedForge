"use client";

import { useCallback, useEffect, useState } from "react";
import { FileText, Loader2 } from "lucide-react";

import { apiGet, type SubmissionRead } from "@/lib/api";
import { formatRelativeTime, formatScore } from "@/lib/format";
import { apiPathForSurface, inferClientSurface } from "@/lib/surface";
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
  const [submissions, setSubmissions] = useState<SubmissionRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSubmissions = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    const surface = inferClientSurface();
    const path = apiPathForSurface(surface, `/competitions/${slug}/submissions/me`);
    try {
      const data = await apiGet<SubmissionRead[]>(path);
      setSubmissions(data);
      onSubmissionsLoaded?.(data);
    } catch (fetchError) {
      const message = fetchError instanceof Error ? fetchError.message : "Failed to load submissions";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [slug, onSubmissionsLoaded]);

  useEffect(() => {
    void fetchSubmissions();
  }, [fetchSubmissions]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="size-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
        <p className="text-sm font-medium text-destructive">{error}</p>
      </div>
    );
  }

  if (submissions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
        <div className="flex size-10 items-center justify-center rounded-full bg-muted">
          <FileText className="size-5 text-muted-foreground" />
        </div>
        <div className="space-y-1">
          <p className="text-sm font-medium">No submissions yet</p>
          <p className="text-xs text-muted-foreground">
            Submit a CSV file to see your results here.
          </p>
        </div>
      </div>
    );
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
          {submissions.map((submission) => (
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
