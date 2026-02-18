"use client";

import { AuthProvider } from "@/components/providers/auth-provider";
import { SessionProvider } from "@/components/providers/session-provider";
import { NotificationProvider } from "@/components/providers/notification-provider";
import { Sidebar } from "@/components/layout/sidebar";
import { AppHeader } from "@/components/layout/app-header";

export default function AppLayout({ children }: { children: React.ReactNode }): React.JSX.Element {
  return (
    <AuthProvider>
      <SessionProvider>
        <NotificationProvider>
          <div className="flex min-h-screen">
            <Sidebar />
            <div className="flex flex-1 flex-col">
              <AppHeader />
              <main className="flex-1 px-6 py-8">{children}</main>
            </div>
          </div>
        </NotificationProvider>
      </SessionProvider>
    </AuthProvider>
  );
}
