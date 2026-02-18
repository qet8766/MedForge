"use client";

import { ErrorPage } from "@/components/feedback/error-page";

export default function RankingsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): React.JSX.Element {
  return <ErrorPage title="Rankings error" error={error} reset={reset} />;
}
