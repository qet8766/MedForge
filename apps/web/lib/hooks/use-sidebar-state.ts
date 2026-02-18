"use client";

import { useCallback, useState } from "react";

const STORAGE_KEY = "medforge-sidebar-collapsed";

function readStoredState(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

export function useSidebarState(): [boolean, (collapsed: boolean) => void] {
  const [collapsed, setCollapsedState] = useState<boolean>(readStoredState);

  const setCollapsed = useCallback((value: boolean) => {
    setCollapsedState(value);
    try {
      localStorage.setItem(STORAGE_KEY, String(value));
    } catch {
      // localStorage unavailable
    }
  }, []);

  return [collapsed, setCollapsed];
}
