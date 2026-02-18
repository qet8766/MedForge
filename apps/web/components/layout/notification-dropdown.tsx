"use client";

import { Bell, CheckCheck, Trash2, Inbox } from "lucide-react";

import { formatRelativeTime } from "@/lib/format";
import { useNotificationContext } from "@/components/providers/notification-provider";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverHeader,
  PopoverTitle,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";

export function NotificationDropdown(): React.JSX.Element {
  const { notifications, unreadCount, markAllRead, clearAll } =
    useNotificationContext();

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon-sm" className="relative">
          <Bell className="size-4" />
          {unreadCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex size-4 items-center justify-center rounded-full bg-primary text-[10px] font-semibold text-primary-foreground">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
          <span className="sr-only">
            Notifications{unreadCount > 0 ? ` (${unreadCount} unread)` : ""}
          </span>
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0">
        <PopoverHeader className="flex flex-row items-center justify-between border-b p-3">
          <PopoverTitle className="text-sm font-semibold">
            Notifications
          </PopoverTitle>
          {notifications.length > 0 && (
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="icon-xs"
                onClick={markAllRead}
                title="Mark all as read"
              >
                <CheckCheck className="size-3" />
              </Button>
              <Button
                variant="ghost"
                size="icon-xs"
                onClick={clearAll}
                title="Clear all"
              >
                <Trash2 className="size-3" />
              </Button>
            </div>
          )}
        </PopoverHeader>

        {notifications.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-8 text-muted-foreground">
            <Inbox className="size-8" />
            <p className="text-sm">No notifications</p>
          </div>
        ) : (
          <ScrollArea className="max-h-72">
            <div className="flex flex-col">
              {notifications.map((notification, index) => (
                <div key={notification.id}>
                  <div className="flex flex-col gap-0.5 px-3 py-2.5">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-medium leading-tight">
                        {!notification.read && (
                          <span className="mr-1.5 inline-block size-1.5 rounded-full bg-primary" />
                        )}
                        {notification.title}
                      </p>
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {formatRelativeTime(notification.timestamp.toISOString())}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {notification.message}
                    </p>
                  </div>
                  {index < notifications.length - 1 && <Separator />}
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </PopoverContent>
    </Popover>
  );
}
