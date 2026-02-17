"use client";

import { useCallback, useEffect, useState } from "react";

import {
  apiGet,
  apiPostJson,
  type MeResponse,
  type SessionActionResponse,
  type SessionCreateResponse,
  type SessionCurrentResponse,
  type SessionRead,
} from "@/lib/api";
import { apiPathForSurface, inferClientSurface } from "@/lib/surface";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { SessionCard } from "@/components/sessions/session-card";
import { SessionControls } from "@/components/sessions/session-controls";

export default function SessionsPage(): React.JSX.Element {
  const surface = inferClientSurface();
  const [status, setStatus] = useState<string>("No session action yet.");
  const [error, setError] = useState<string>("");
  const [currentSession, setCurrentSession] = useState<SessionRead | null>(null);

  const rehydrateCurrentSession = useCallback(async (announce: boolean): Promise<void> => {
    try {
      const response = await apiGet<SessionCurrentResponse>(
        apiPathForSurface(surface, "/sessions/current")
      );
      setCurrentSession(response.session);
      if (!announce) return;
      if (response.session) {
        setStatus(
          `Recovered active session ${response.session.slug} (${response.session.status}).`
        );
      } else {
        setStatus("No active session.");
      }
    } catch (requestError) {
      if (announce) setStatus("Not authenticated.");
      setCurrentSession(null);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to fetch session state."
      );
    }
  }, []);

  useEffect(() => {
    setError("");
    void rehydrateCurrentSession(true);
  }, [rehydrateCurrentSession]);

  async function handleWhoAmI(): Promise<void> {
    setError("");
    try {
      const me = await apiGet<MeResponse>("/api/v2/me");
      setStatus(
        `Signed in as ${me.email ?? me.user_id} (${me.role}). Internal access: ${me.can_use_internal ? "yes" : "no"}.`
      );
      await rehydrateCurrentSession(false);
    } catch (requestError) {
      setStatus("Not authenticated.");
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to fetch session state."
      );
    }
  }

  async function handleCreateSession(): Promise<void> {
    setError("");
    try {
      const response = await apiPostJson<SessionCreateResponse>(
        apiPathForSurface(surface, "/sessions"),
        {}
      );
      setStatus(
        `${response.message} Slug: ${response.session.slug}, GPU: ${response.session.gpu_id}, status: ${response.session.status}.`
      );
      await rehydrateCurrentSession(false);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Session creation failed."
      );
    }
  }

  async function handleStopSession(): Promise<void> {
    setError("");
    if (!currentSession) {
      setError("No session selected to stop.");
      return;
    }
    try {
      const response = await apiPostJson<SessionActionResponse>(
        apiPathForSurface(surface, `/sessions/${currentSession.id}/stop`),
        {}
      );
      setStatus(response.message);
      await rehydrateCurrentSession(false);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Session stop failed."
      );
    }
  }

  async function handleLogout(): Promise<void> {
    setError("");
    try {
      await apiPostJson<SessionActionResponse>("/api/v2/auth/logout", {});
      setStatus("Signed out.");
      setCurrentSession(null);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Sign out failed."
      );
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Sessions</h1>
        <p className="text-muted-foreground">
          Create an {surface.toUpperCase()} session, then request stop.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Session Controls</CardTitle>
          <CardDescription>Manage your GPU-backed development sessions</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <SessionControls
            surfaceLabel={surface.toUpperCase()}
            hasSession={currentSession !== null}
            onCreateSession={handleCreateSession}
            onStopSession={handleStopSession}
            onWhoAmI={handleWhoAmI}
            onLogout={handleLogout}
          />

          <p className="text-sm text-muted-foreground" data-testid="session-status">
            {status}
          </p>

          {currentSession ? (
            <SessionCard session={currentSession} />
          ) : null}
        </CardContent>
      </Card>

      {error ? (
        <Alert variant="destructive" data-testid="session-error">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}
