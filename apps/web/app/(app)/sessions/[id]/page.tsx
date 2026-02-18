"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import {
  apiGet,
  apiPostJson,
  type SessionActionResponse,
  type SessionRead,
} from "@/lib/api";
import { apiPathForSurface, inferClientSurface } from "@/lib/surface";
import { isTransitioning } from "@/lib/status";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { SessionDetail } from "@/components/sessions/session-detail";

export default function SessionDetailPage(): React.JSX.Element {
  const params = useParams<{ id: string }>();
  const sessionId = params.id;
  const surface = inferClientSurface();

  const [session, setSession] = useState<SessionRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSession = useCallback(async (): Promise<void> => {
    try {
      const result = await apiGet<SessionRead>(
        apiPathForSurface(surface, `/sessions/${sessionId}`)
      );
      setSession(result);
      setError(null);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load session.";
      setError(message);
      setSession(null);
    } finally {
      setLoading(false);
    }
  }, [surface, sessionId]);

  useEffect(() => {
    void fetchSession();
  }, [fetchSession]);

  useEffect(() => {
    if (!session || !isTransitioning(session.status)) return;

    const interval = setInterval(() => {
      void fetchSession();
    }, 3000);

    return () => clearInterval(interval);
  }, [session, fetchSession]);

  async function handleStop(): Promise<void> {
    if (!session) return;
    try {
      await apiPostJson<SessionActionResponse>(
        apiPathForSurface(surface, `/sessions/${session.id}/stop`),
        {}
      );
      toast.success("Session stop requested.");
      await fetchSession();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to stop session.";
      toast.error(message);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="size-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !session) {
    return (
      <Alert variant="destructive">
        <AlertDescription>{error ?? "Session not found."}</AlertDescription>
      </Alert>
    );
  }

  return <SessionDetail session={session} onStop={handleStop} />;
}
