"use client";

import { useCallback, useEffect, useState } from "react";

import { apiGet, apiPatchJson, type UserAdminRead, type UserUpdateRequest } from "@/lib/api";
import { formatRelativeTime, getErrorMessage } from "@/lib/format";
import { useApiMutation } from "@/lib/hooks/use-api-mutation";
import { useFetchState } from "@/lib/hooks/use-fetch-state";
import { TableErrorState } from "@/components/shared/table-states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const COLUMN_COUNT = 6;

function UserTableHeader(): React.JSX.Element {
  return (
    <TableHeader>
      <TableRow>
        <TableHead>Email</TableHead>
        <TableHead>Role</TableHead>
        <TableHead>Internal Access</TableHead>
        <TableHead>Max Sessions</TableHead>
        <TableHead>Active Sessions</TableHead>
        <TableHead>Created</TableHead>
      </TableRow>
    </TableHeader>
  );
}

function UserTableSkeleton(): React.JSX.Element {
  return (
    <Table>
      <UserTableHeader />
      <TableBody>
        {Array.from({ length: 5 }).map((_, i) => (
          <TableRow key={i}>
            <TableCell><Skeleton className="h-4 w-40" /></TableCell>
            <TableCell><Skeleton className="h-5 w-14" /></TableCell>
            <TableCell><Skeleton className="h-4 w-10" /></TableCell>
            <TableCell><Skeleton className="h-4 w-12" /></TableCell>
            <TableCell><Skeleton className="h-4 w-8" /></TableCell>
            <TableCell><Skeleton className="h-4 w-16" /></TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function UserRow({
  user,
  onUpdated,
}: {
  user: UserAdminRead;
  onUpdated: (updated: UserAdminRead) => void;
}): React.JSX.Element {
  const [editingMaxValue, setEditingMaxValue] = useState<string | null>(null);

  const roleMutation = useApiMutation(
    (userId: string, role: "user" | "admin") =>
      apiPatchJson<UserAdminRead>(`/api/v2/admin/users/${userId}`, { role } satisfies UserUpdateRequest),
    {
      successMessage: "Role updated.",
      onSuccess: onUpdated,
    }
  );

  const internalMutation = useApiMutation(
    (userId: string, canUseInternal: boolean) =>
      apiPatchJson<UserAdminRead>(`/api/v2/admin/users/${userId}`, { can_use_internal: canUseInternal } satisfies UserUpdateRequest),
    {
      successMessage: "Internal access updated.",
      onSuccess: onUpdated,
    }
  );

  const maxSessionsMutation = useApiMutation(
    (userId: string, maxConcurrentSessions: number) =>
      apiPatchJson<UserAdminRead>(`/api/v2/admin/users/${userId}`, { max_concurrent_sessions: maxConcurrentSessions } satisfies UserUpdateRequest),
    {
      successMessage: "Max sessions updated.",
      onSuccess: (updated) => {
        setEditingMaxValue(null);
        onUpdated(updated);
      },
    }
  );

  function handleRoleChange(newRole: string): void {
    if (newRole === "user" || newRole === "admin") {
      void roleMutation.mutate(user.user_id, newRole);
    }
  }

  function handleInternalToggle(checked: boolean): void {
    void internalMutation.mutate(user.user_id, checked);
  }

  function handleMaxSessionsSubmit(): void {
    if (editingMaxValue === null) return;
    const parsed = parseInt(editingMaxValue, 10);
    if (Number.isNaN(parsed) || parsed < 1) return;
    void maxSessionsMutation.mutate(user.user_id, parsed);
  }

  const isMutating = roleMutation.loading || internalMutation.loading || maxSessionsMutation.loading;
  const roleBadgeVariant = user.role === "admin" ? "default" as const : "secondary" as const;

  return (
    <TableRow>
      <TableCell className="font-medium">{user.email}</TableCell>
      <TableCell>
        <Select value={user.role} onValueChange={handleRoleChange} disabled={isMutating}>
          <SelectTrigger size="sm" className="w-24">
            <SelectValue>
              <Badge variant={roleBadgeVariant}>{user.role}</Badge>
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="user">user</SelectItem>
            <SelectItem value="admin">admin</SelectItem>
          </SelectContent>
        </Select>
      </TableCell>
      <TableCell>
        <Switch
          checked={user.can_use_internal}
          onCheckedChange={handleInternalToggle}
          disabled={isMutating}
          size="sm"
        />
      </TableCell>
      <TableCell>
        {editingMaxValue !== null ? (
          <form
            className="flex items-center gap-1"
            onSubmit={(e) => {
              e.preventDefault();
              handleMaxSessionsSubmit();
            }}
          >
            <Input
              type="number"
              min={1}
              value={editingMaxValue}
              onChange={(e) => setEditingMaxValue(e.target.value)}
              className="h-7 w-16 text-sm"
              disabled={maxSessionsMutation.loading}
              autoFocus
            />
            <Button type="submit" size="xs" disabled={maxSessionsMutation.loading}>
              Save
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="xs"
              onClick={() => setEditingMaxValue(null)}
              disabled={maxSessionsMutation.loading}
            >
              Cancel
            </Button>
          </form>
        ) : (
          <Button
            variant="ghost"
            size="xs"
            onClick={() => setEditingMaxValue(String(user.max_concurrent_sessions))}
            disabled={isMutating}
          >
            {user.max_concurrent_sessions}
          </Button>
        )}
      </TableCell>
      <TableCell>{user.active_session_count}</TableCell>
      <TableCell className="text-muted-foreground">{formatRelativeTime(user.created_at)}</TableCell>
    </TableRow>
  );
}

export function UserTable(): React.JSX.Element {
  const [state, setState] = useFetchState<UserAdminRead[]>([]);

  const fetchUsers = useCallback(async (): Promise<void> => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const users = await apiGet<UserAdminRead[]>("/api/v2/admin/users");
      setState({ data: users, loading: false, error: null });
    } catch (err) {
      const message = getErrorMessage(err, "Failed to load users.");
      setState({ data: [], loading: false, error: message });
    }
  }, [setState]);

  useEffect(() => {
    void fetchUsers();
  }, [fetchUsers]);

  function handleUserUpdated(updated: UserAdminRead): void {
    setState((prev) => ({
      ...prev,
      data: prev.data.map((u) => (u.user_id === updated.user_id ? updated : u)),
    }));
  }

  if (state.loading) {
    return <UserTableSkeleton />;
  }

  if (state.error !== null) {
    return <TableErrorState message={state.error} />;
  }

  if (state.data.length === 0) {
    return (
      <Table>
        <UserTableHeader />
        <TableBody>
          <TableRow>
            <TableCell colSpan={COLUMN_COUNT} className="text-center text-muted-foreground">
              No users found.
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
  }

  return (
    <Table>
      <UserTableHeader />
      <TableBody>
        {state.data.map((user) => (
          <UserRow key={user.user_id} user={user} onUpdated={handleUserUpdated} />
        ))}
      </TableBody>
    </Table>
  );
}
