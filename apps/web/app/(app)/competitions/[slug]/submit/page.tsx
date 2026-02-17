"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { AlertCircle, CheckCircle2 } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { SubmissionForm } from "@/components/submissions/submission-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

export default function CompetitionSubmitPage(): React.JSX.Element {
  const params = useParams();
  const rawSlug = params.slug;
  const slug = Array.isArray(rawSlug) ? rawSlug[0] : rawSlug;

  const [result, setResult] = useState<string>("");
  const [error, setError] = useState<string>("");

  return (
    <div className="space-y-8">
      <PageHeader
        title="Submit"
        description={`Upload your predictions for ${slug ?? "this competition"}.`}
      />

      <div className="grid gap-8 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <Card>
            <CardHeader>
              <CardTitle>Upload Predictions</CardTitle>
              <CardDescription>
                Drag and drop your CSV file or click to browse. Only .csv files are accepted.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <SubmissionForm
                slug={slug ?? ""}
                onResult={setResult}
                onError={setError}
              />
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6 lg:col-span-2">
          {error ? (
            <Alert variant="destructive">
              <AlertCircle className="size-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}

          {result ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle2 className="size-4 text-green-500" />
                  Submission Result
                </CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="overflow-x-auto rounded-lg bg-muted p-4 font-mono text-xs leading-relaxed">
                  {result}
                </pre>
              </CardContent>
            </Card>
          ) : null}

          {!error && !result ? (
            <Card>
              <CardContent className="py-8">
                <div className="space-y-3 text-sm text-muted-foreground">
                  <p className="font-medium text-foreground">Submission guidelines</p>
                  <ul className="list-inside list-disc space-y-1.5">
                    <li>File must be in CSV format</li>
                    <li>Columns should match the expected schema</li>
                    <li>Results will appear here after scoring</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
