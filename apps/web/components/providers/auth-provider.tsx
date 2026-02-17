"use client";

import { createContext, useContext } from "react";

import { useAuth } from "@/lib/hooks/use-auth";
import type { MeResponse } from "@/lib/api";

type AuthContextValue = {
  user: MeResponse | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

type AuthProviderProps = {
  children: React.ReactNode;
};

export function AuthProvider({ children }: AuthProviderProps): React.JSX.Element {
  const auth = useAuth();

  return (
    <AuthContext.Provider value={auth}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuthContext must be used within an AuthProvider.");
  }
  return context;
}
