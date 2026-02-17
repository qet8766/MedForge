import { PageHeader } from "@/components/layout/page-header";
import { SubmissionHistory } from "@/components/submissions/submission-history";
import { ScoreChart } from "@/components/submissions/score-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface HistoryPageProps {
  params: Promise<{ slug: string }>;
}

export default async function CompetitionHistoryPage({
  params,
}: HistoryPageProps): Promise<React.JSX.Element> {
  const { slug } = await params;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Submission History"
        description={`Review your past submissions for ${slug}.`}
      />

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Past Submissions</CardTitle>
          </CardHeader>
          <CardContent>
            <SubmissionHistory slug={slug} />
          </CardContent>
        </Card>

        <ScoreChart slug={slug} />
      </div>
    </div>
  );
}
