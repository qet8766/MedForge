"use client";

import { useState } from "react";
import { apiSubmitFile } from "../../../../lib/api";

export default function CompetitionSubmitPage({
  params
}: {
  params: { slug: string };
}): React.JSX.Element {
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
      const payload = await apiSubmitFile(`/api/competitions/${params.slug}/submissions`, file);
      setResult(JSON.stringify(payload, null, 2));
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Submission failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="grid" style={{ maxWidth: 680 }}>
      <h1>Submit · {params.slug}</h1>
      <p className="muted">
        Alpha scoring is always-on with hidden holdout labels. Only CSV submissions are accepted.
      </p>
      <form onSubmit={handleSubmit} className="card">
        <div>
          <label htmlFor="submission">Prediction CSV</label>
          <input
            id="submission"
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </div>
        <div>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Submitting..." : "Submit"}
          </button>
        </div>
      </form>
      {error ? <pre className="card" style={{ color: "#a11" }}>{error}</pre> : null}
      {result ? <pre className="card">{result}</pre> : null}
    </section>
  );
}
