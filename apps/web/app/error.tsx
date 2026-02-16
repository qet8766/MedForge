"use client";

import { ErrorPage } from "@/components/ErrorPage";

export default function RootError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): React.JSX.Element {
  return <ErrorPage title="Something went wrong" error={error} reset={reset} />;
}
