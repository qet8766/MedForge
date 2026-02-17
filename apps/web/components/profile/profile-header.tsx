"use client";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";

interface ProfileHeaderProps {
  handle: string;
}

export function ProfileHeader({ handle }: ProfileHeaderProps): React.JSX.Element {
  const initials = handle.slice(0, 2).toUpperCase();

  return (
    <div className="flex items-center gap-4">
      <Avatar size="lg">
        <AvatarFallback>{initials}</AvatarFallback>
      </Avatar>
      <div className="space-y-1">
        <h2 className="text-lg font-semibold">{handle}</h2>
        <Badge variant="secondary">Member</Badge>
      </div>
    </div>
  );
}
