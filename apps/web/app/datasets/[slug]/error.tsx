"use client";

import { ErrorPage } from "@/components/ErrorPage";

export default function DatasetError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): React.JSX.Element {
  return <ErrorPage title="Dataset error" error={error} reset={reset} />;
}
