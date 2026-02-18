"use client";

import { useCallback, useState } from "react";

import { toast } from "sonner";

type MutationState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

type UseApiMutationOptions<T> = {
  onSuccess?: (data: T) => void;
  successMessage?: string;
  errorMessage?: string;
};

type UseApiMutationReturn<TArgs extends unknown[], T> = MutationState<T> & {
  mutate: (...args: TArgs) => Promise<T | null>;
  reset: () => void;
};

export function useApiMutation<TArgs extends unknown[], T>(
  mutationFn: (...args: TArgs) => Promise<T>,
  options: UseApiMutationOptions<T> = {}
): UseApiMutationReturn<TArgs, T> {
  const [state, setState] = useState<MutationState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const { successMessage, errorMessage, onSuccess } = options;

  const mutate = useCallback(
    async (...args: TArgs): Promise<T | null> => {
      setState({ data: null, loading: true, error: null });
      try {
        const result = await mutationFn(...args);
        setState({ data: result, loading: false, error: null });
        if (successMessage) {
          toast.success(successMessage);
        }
        onSuccess?.(result);
        return result;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : (errorMessage ?? "An error occurred.");
        setState({ data: null, loading: false, error: message });
        toast.error(message);
        return null;
      }
    },
    [mutationFn, successMessage, errorMessage, onSuccess]
  );

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  return { ...state, mutate, reset };
}
