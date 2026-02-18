import { useCallback, useEffect, useRef, useState } from "react";

import { apiGet, type SessionCurrentResponse, type SessionRead } from "@/lib/api";
import { getErrorMessage } from "@/lib/format";
import { isTransitioning } from "@/lib/status";
import { apiPathForSurface, inferClientSurface } from "@/lib/surface";

type UseSessionPollingReturn = {
  session: SessionRead | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
};

const DEFAULT_POLL_INTERVAL_MS = 3000;

export function useSessionPolling(
  pollInterval: number = DEFAULT_POLL_INTERVAL_MS
): UseSessionPollingReturn {
  const [session, setSession] = useState<SessionRead | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(() => {
    setRefreshToken((t) => t + 1);
  }, []);

  const fetchSession = useCallback(async (): Promise<SessionRead | null> => {
    const surface = inferClientSurface();
    const path = apiPathForSurface(surface, "/sessions/current");
    const response = await apiGet<SessionCurrentResponse>(path);
    return response.session;
  }, []);

  const poll = useCallback(async (): Promise<void> => {
    try {
      const current = await fetchSession();
      setSession(current);
      setError(null);
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Failed to fetch session."));
      setSession(null);
    } finally {
      setLoading(false);
    }
  }, [fetchSession]);

  useEffect(() => {
    void poll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [poll, refreshToken]);

  useEffect(() => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    const shouldPoll = session !== null && isTransitioning(session.status);
    if (!shouldPoll) {
      return;
    }

    timerRef.current = setInterval(() => {
      void poll();
    }, pollInterval);

    return () => {
      if (timerRef.current !== null) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [session, pollInterval, poll]);

  return { session, loading, error, refresh };
}
