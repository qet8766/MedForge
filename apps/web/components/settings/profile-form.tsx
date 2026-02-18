"use client";

import { type FormEvent, useState } from "react";

import { apiPatchJson, type MeResponse } from "@/lib/api";
import { useApiMutation } from "@/lib/hooks/use-api-mutation";
import { useAuthContext } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function ProfileForm(): React.JSX.Element {
  const { user, refresh } = useAuthContext();
  const [email, setEmail] = useState(user?.email ?? "");

  const { mutate, loading } = useApiMutation<[string], MeResponse>(
    (newEmail: string) => apiPatchJson<MeResponse>("/api/v2/me", { email: newEmail }),
    {
      successMessage: "Profile updated.",
      onSuccess: () => refresh(),
    },
  );

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const trimmed = email.trim();
    if (trimmed.length === 0) {
      return;
    }
    void mutate(trimmed);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Profile</CardTitle>
        <CardDescription>Update your email address.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="profile-email">Email</Label>
            <Input
              id="profile-email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <Button type="submit" disabled={loading}>
            {loading ? "Saving..." : "Save"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
