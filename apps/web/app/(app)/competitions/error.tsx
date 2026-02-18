"use client";

import { ErrorPage } from "@/components/feedback/error-page";

export default function CompetitionsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): React.JSX.Element {
  return <ErrorPage title="Competitions error" error={error} reset={reset} />;
}
