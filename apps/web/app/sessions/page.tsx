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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";

function statusVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "running":
      return "default";
    case "starting":
      return "outline";
    case "stopped":
    case "stopping":
      return "secondary";
    case "error":
      return "destructive";
    default:
      return "outline";
  }
}

export default function SessionsPage(): React.JSX.Element {
  const [status, setStatus] = useState<string>("No session action yet.");
  const [error, setError] = useState<string>("");
  const [currentSession, setCurrentSession] = useState<SessionRead | null>(null);

  const rehydrateCurrentSession = useCallback(async (announce: boolean): Promise<void> => {
    try {
      const response = await apiGet<SessionCurrentResponse>("/api/sessions/current");
      setCurrentSession(response.session);
      if (!announce) {
        return;
      }
      if (response.session) {
        setStatus(`Recovered active session ${response.session.slug} (${response.session.status}).`);
      } else {
        setStatus("No active session.");
      }
    } catch (requestError) {
      if (announce) {
        setStatus("Not authenticated.");
      }
      setCurrentSession(null);
      setError(requestError instanceof Error ? requestError.message : "Unable to fetch session state.");
    }
  }, []);

  useEffect(() => {
    setError("");
    void rehydrateCurrentSession(true);
  }, [rehydrateCurrentSession]);

  async function handleWhoAmI(): Promise<void> {
    setError("");
    try {
      const me = await apiGet<MeResponse>("/api/me");
      setStatus(`Signed in as ${me.email ?? me.user_id} (${me.role}).`);
      await rehydrateCurrentSession(false);
    } catch (requestError) {
      setStatus("Not authenticated.");
      setError(requestError instanceof Error ? requestError.message : "Unable to fetch session state.");
    }
  }

  async function handleCreateSession(): Promise<void> {
    setError("");
    try {
      const response = await apiPostJson<SessionCreateResponse>("/api/sessions", { tier: "PUBLIC" });
      setStatus(
        `${response.detail} Slug: ${response.session.slug}, GPU: ${response.session.gpu_id}, status: ${response.session.status}.`
      );
      await rehydrateCurrentSession(false);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Session creation failed.");
    }
  }

  async function handleStopSession(): Promise<void> {
    setError("");
    if (!currentSession) {
      setError("No session selected to stop.");
      return;
    }

    try {
      const response = await apiPostJson<SessionActionResponse>(`/api/sessions/${currentSession.id}/stop`, {});
      setStatus(response.detail);
      await rehydrateCurrentSession(false);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Session stop failed.");
    }
  }

  async function handleLogout(): Promise<void> {
    setError("");
    try {
      await apiPostJson<{ detail: string }>("/api/auth/logout", {});
      setStatus("Signed out.");
      setCurrentSession(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Sign out failed.");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Sessions</h1>
        <p className="text-muted-foreground">
          Create a PUBLIC session, then request stop. Stop is asynchronous and final state arrives via recovery.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Session Controls</CardTitle>
          <CardDescription>Manage your GPU-backed development sessions</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <Button onClick={handleCreateSession} data-testid="session-create">
              Create PUBLIC Session
            </Button>
            <Button
              variant="outline"
              onClick={handleStopSession}
              disabled={!currentSession}
              data-testid="session-stop"
            >
              Stop Current Session
            </Button>
            <Button variant="secondary" onClick={handleWhoAmI} data-testid="session-whoami">
              Check /api/me
            </Button>
            <Button variant="ghost" onClick={handleLogout} data-testid="session-logout">
              Sign out
            </Button>
          </div>

          <p className="text-sm text-muted-foreground" data-testid="session-status">{status}</p>

          {currentSession ? (
            <div className="rounded-lg border border-border bg-muted/50 p-4 space-y-2">
              <p className="text-sm" data-testid="session-current">
                <span className="text-muted-foreground">Session:</span>{" "}
                <span className="font-mono">{currentSession.id}</span>
                {" | slug: "}
                <span className="font-mono">{currentSession.slug}</span>
                {" | status: "}
                <Badge variant={statusVariant(currentSession.status)}>{currentSession.status}</Badge>
              </p>
              <p className="font-mono text-sm" data-testid="session-slug">
                {currentSession.slug}
              </p>
            </div>
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
