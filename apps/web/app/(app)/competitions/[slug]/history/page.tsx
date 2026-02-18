"use client";

import { useCallback, useState } from "react";
import { useParams } from "next/navigation";

import type { SubmissionRead } from "@/lib/api";
import { SubmissionHistory } from "@/components/submissions/submission-history";
import { ScoreChart } from "@/components/submissions/score-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function CompetitionHistoryPage(): React.JSX.Element {
  const params = useParams();
  const rawSlug = params.slug;
  const slug = Array.isArray(rawSlug) ? rawSlug[0] : rawSlug;

  const [submissions, setSubmissions] = useState<SubmissionRead[]>([]);

  const handleSubmissionsLoaded = useCallback((data: SubmissionRead[]): void => {
    setSubmissions(data);
  }, []);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Past Submissions</CardTitle>
        </CardHeader>
        <CardContent>
          <SubmissionHistory
            slug={slug ?? ""}
            onSubmissionsLoaded={handleSubmissionsLoaded}
          />
        </CardContent>
      </Card>

      <ScoreChart submissions={submissions} />
    </div>
  );
}
