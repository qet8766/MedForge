"use client";

import { ErrorPage } from "@/components/feedback/error-page";

export default function SessionsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): React.JSX.Element {
  return <ErrorPage title="Sessions error" error={error} reset={reset} />;
}
