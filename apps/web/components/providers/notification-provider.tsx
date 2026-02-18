"use client";

import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";

type Notification = {
  id: string;
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
};

type NotificationContextValue = {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (title: string, message: string) => void;
  markAllRead: () => void;
  clearAll: () => void;
};

const NotificationContext = createContext<NotificationContextValue | null>(null);

type NotificationProviderProps = {
  children: React.ReactNode;
};

export function NotificationProvider({ children }: NotificationProviderProps): React.JSX.Element {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const counterRef = useRef(0);

  const unreadCount = useMemo(
    () => notifications.filter((n) => !n.read).length,
    [notifications]
  );

  const addNotification = useCallback((title: string, message: string) => {
    counterRef.current += 1;
    const notification: Notification = {
      id: `notif-${counterRef.current}`,
      title,
      message,
      timestamp: new Date(),
      read: false,
    };
    setNotifications((prev) => [notification, ...prev].slice(0, 50));
  }, []);

  const markAllRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  const value = useMemo<NotificationContextValue>(
    () => ({ notifications, unreadCount, addNotification, markAllRead, clearAll }),
    [notifications, unreadCount, addNotification, markAllRead, clearAll]
  );

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotificationContext(): NotificationContextValue {
  const context = useContext(NotificationContext);
  if (context === null) {
    throw new Error("useNotificationContext must be used within a NotificationProvider.");
  }
  return context;
}
