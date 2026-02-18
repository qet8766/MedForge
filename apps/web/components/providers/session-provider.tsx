"use client";

import { createContext, useCallback, useContext, useMemo } from "react";

import {
  apiPostJson,
  type SessionActionResponse,
  type SessionCreateResponse,
  type SessionRead,
} from "@/lib/api";
import { useSessionPolling } from "@/lib/hooks/use-session-polling";
import { apiPathForSurface, inferClientSurface } from "@/lib/surface";

type SessionContextValue = {
  session: SessionRead | null;
  loading: boolean;
  error: string | null;
  createSession: () => Promise<SessionCreateResponse | null>;
  stopSession: () => Promise<void>;
  refresh: () => void;
};

const SessionContext = createContext<SessionContextValue | null>(null);

type SessionProviderProps = {
  children: React.ReactNode;
};

export function SessionProvider({ children }: SessionProviderProps): React.JSX.Element {
  const { session, loading, error } = useSessionPolling();
  const surface = inferClientSurface();

  const createSession = useCallback(async (): Promise<SessionCreateResponse | null> => {
    try {
      const response = await apiPostJson<SessionCreateResponse>(
        apiPathForSurface(surface, "/sessions"),
        {}
      );
      return response;
    } catch {
      return null;
    }
  }, [surface]);

  const stopSession = useCallback(async (): Promise<void> => {
    if (!session) return;
    try {
      await apiPostJson<SessionActionResponse>(
        apiPathForSurface(surface, `/sessions/${session.id}/stop`),
        {}
      );
    } catch {
      // handled by polling
    }
  }, [session, surface]);

  const refresh = useCallback(() => {
    // Re-trigger by navigation; polling will pick it up
  }, []);

  const value = useMemo<SessionContextValue>(
    () => ({ session, loading, error, createSession, stopSession, refresh }),
    [session, loading, error, createSession, stopSession, refresh]
  );

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSessionContext(): SessionContextValue {
  const context = useContext(SessionContext);
  if (context === null) {
    throw new Error("useSessionContext must be used within a SessionProvider.");
  }
  return context;
}
