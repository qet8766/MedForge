import { useEffect, useRef } from "react";

export function usePolling(
  fn: () => void,
  intervalMs: number,
  enabled: boolean,
): void {
  const fnRef = useRef(fn);
  useEffect(() => {
    fnRef.current = fn;
  });

  useEffect(() => {
    if (!enabled) return;

    const id = setInterval(() => {
      fnRef.current();
    }, intervalMs);

    return () => {
      clearInterval(id);
    };
  }, [enabled, intervalMs]);
}
