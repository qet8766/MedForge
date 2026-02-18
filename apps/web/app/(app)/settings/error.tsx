"use client";

import { ErrorPage } from "@/components/feedback/error-page";

export default function SettingsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): React.JSX.Element {
  return <ErrorPage title="Settings error" error={error} reset={reset} />;
}
