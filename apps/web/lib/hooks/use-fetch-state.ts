import { useState } from "react";

export type FetchState<T> = {
  data: T;
  loading: boolean;
  error: string | null;
};

export function useFetchState<T>(
  initial: T,
): [FetchState<T>, React.Dispatch<React.SetStateAction<FetchState<T>>>] {
  return useState<FetchState<T>>({
    data: initial,
    loading: true,
    error: null,
  });
}
