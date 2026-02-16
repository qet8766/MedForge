"use client";

import { useCallback, useEffect, useState } from "react";
import {
  apiGet,
  apiPostJson,
  type MeResponse,
  type SessionCreateResponse,
  type SessionCurrentResponse,
  type SessionRead,
  type SessionStopResponse
} from "../../lib/api";

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
      const response = await apiPostJson<SessionStopResponse>(`/api/sessions/${currentSession.id}/stop`, {});
      setStatus(`${response.detail} Current state: ${response.session.status}.`);
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
    <section className="card">
      <h1>Sessions</h1>
      <p>
        Create a PUBLIC session, then stop it. The API now returns live lifecycle state for each action.
      </p>
      <div className="grid" style={{ gap: 10, maxWidth: 280 }}>
        <button type="button" onClick={handleCreateSession} data-testid="session-create">Create PUBLIC Session</button>
        <button type="button" onClick={handleStopSession} disabled={!currentSession} data-testid="session-stop">Stop Current Session</button>
        <button type="button" onClick={handleWhoAmI} data-testid="session-whoami">Check /api/me</button>
        <button type="button" onClick={handleLogout} data-testid="session-logout">Sign out</button>
      </div>
      <p className="muted" data-testid="session-status">{status}</p>
      {currentSession ? (
        <p className="muted" data-testid="session-current">
          Session: {currentSession.id} | slug: {currentSession.slug} | status: {currentSession.status}
        </p>
      ) : null}
      {currentSession ? (
        <p className="muted" data-testid="session-slug">
          {currentSession.slug}
        </p>
      ) : null}
      {error ? <p className="muted" style={{ color: "#a11" }} data-testid="session-error">{error}</p> : null}
    </section>
  );
}
