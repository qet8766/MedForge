"use client";

import { ErrorPage } from "@/components/ErrorPage";

export default function CompetitionError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): React.JSX.Element {
  return <ErrorPage title="Competition error" error={error} reset={reset} />;
}
