"use client";

import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";

interface ErrorPageProps {
  title: string;
  error: Error & { digest?: string };
  reset: () => void;
}

export function ErrorPage({ title, error, reset }: ErrorPageProps): React.JSX.Element {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6 px-6 text-center">
      <div className="flex size-16 items-center justify-center rounded-full bg-destructive/10">
        <AlertTriangle className="size-8 text-destructive" />
      </div>
      <div className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        <p className="max-w-md text-muted-foreground">{error.message}</p>
        {error.digest ? (
          <p className="font-mono text-xs text-muted-foreground/60">Digest: {error.digest}</p>
        ) : null}
      </div>
      <Button onClick={reset} variant="outline">
        Try again
      </Button>
    </div>
  );
}
