"use client";

import { type FormEvent, useState } from "react";

import { apiPatchJson, type MeResponse } from "@/lib/api";
import { useApiMutation } from "@/lib/hooks/use-api-mutation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function AccountForm(): React.JSX.Element {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const { mutate, loading } = useApiMutation<[string, string], MeResponse>(
    (current: string, next: string) =>
      apiPatchJson<MeResponse>("/api/v2/me", {
        current_password: current,
        new_password: next,
      }),
    {
      successMessage: "Password updated.",
      onSuccess: () => {
        setCurrentPassword("");
        setNewPassword("");
      },
    },
  );

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (currentPassword.length === 0 || newPassword.length === 0) {
      return;
    }
    void mutate(currentPassword, newPassword);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Change Password</CardTitle>
        <CardDescription>
          Enter your current password and choose a new one.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="current-password">Current Password</Label>
            <Input
              id="current-password"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="new-password">New Password</Label>
            <Input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
          </div>
          <Button type="submit" disabled={loading}>
            {loading ? "Updating..." : "Update Password"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
