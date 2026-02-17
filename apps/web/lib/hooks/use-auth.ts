import { useCallback, useEffect, useState } from "react";

import { apiGet, type MeResponse } from "@/lib/api";

type UseAuthReturn = {
  user: MeResponse | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
};

export function useAuth(): UseAuthReturn {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUser = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const me = await apiGet<MeResponse>("/api/v2/me");
      setUser(me);
    } catch (requestError) {
      setUser(null);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Failed to fetch user."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchUser();
  }, [fetchUser]);

  const refresh = useCallback((): void => {
    void fetchUser();
  }, [fetchUser]);

  return { user, loading, error, refresh };
}
