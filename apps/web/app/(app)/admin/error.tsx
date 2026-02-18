"use client";

import { ErrorPage } from "@/components/feedback/error-page";

export default function AdminError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): React.JSX.Element {
  return <ErrorPage title="Admin error" error={error} reset={reset} />;
}
