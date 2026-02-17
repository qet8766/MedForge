"use client";

import { useState } from "react";
import { useParams } from "next/navigation";

import { apiSubmitFile } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";

export default function CompetitionSubmitPage(): React.JSX.Element {
  const params = useParams();
  const rawSlug = params.slug;
  const slug = Array.isArray(rawSlug) ? rawSlug[0] : rawSlug;

  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError("");
    setResult("");

    if (!file) {
      setError("Choose a CSV file first.");
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = await apiSubmitFile(`/api/competitions/${slug}/submissions`, file);
      setResult(JSON.stringify(payload, null, 2));
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Submission failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Submit</h1>
        <p className="text-muted-foreground">{slug}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Upload Predictions</CardTitle>
          <CardDescription>
            Alpha scoring is always-on with hidden holdout labels. Only CSV submissions are accepted.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="submission">Prediction CSV</Label>
              <Input
                id="submission"
                type="file"
                accept=".csv,text/csv"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            </div>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Submitting..." : "Submit"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {result ? (
        <Card>
          <CardContent className="pt-6">
            <pre className="overflow-x-auto font-mono text-sm">{result}</pre>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
