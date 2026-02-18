"use client";

import { type FormEvent, useState } from "react";

import { apiPatchJson, type MeResponse } from "@/lib/api";
import { useApiMutation } from "@/lib/hooks/use-api-mutation";
import { useAuthContext } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

const SSH_KEY_PREFIXES = ["ssh-rsa ", "ssh-ed25519 ", "ecdsa-sha2-", "sk-ssh-"];

function isValidSshKey(key: string): boolean {
  return SSH_KEY_PREFIXES.some((prefix) => key.startsWith(prefix));
}

export function ProfileForm(): React.JSX.Element {
  const { user, refresh } = useAuthContext();
  const [email, setEmail] = useState(user?.email ?? "");
  const [sshKey, setSshKey] = useState(user?.ssh_public_key ?? "");
  const [sshKeyError, setSshKeyError] = useState<string | null>(null);

  const { mutate: mutateEmail, loading: emailLoading } = useApiMutation<[string], MeResponse>(
    (newEmail: string) => apiPatchJson<MeResponse>("/api/v2/me", { email: newEmail }),
    {
      successMessage: "Email updated.",
      onSuccess: () => refresh(),
    },
  );

  const { mutate: mutateSshKey, loading: sshKeyLoading } = useApiMutation<[string | null], MeResponse>(
    (key: string | null) => apiPatchJson<MeResponse>("/api/v2/me", { ssh_public_key: key }),
    {
      successMessage: "SSH key updated.",
      onSuccess: () => refresh(),
    },
  );

  function handleEmailSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const trimmed = email.trim();
    if (trimmed.length === 0) {
      return;
    }
    void mutateEmail(trimmed);
  }

  function handleSshKeySubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    setSshKeyError(null);
    const trimmed = sshKey.trim();
    if (trimmed.length === 0) {
      void mutateSshKey(null);
      return;
    }
    if (!isValidSshKey(trimmed)) {
      setSshKeyError("Key must start with ssh-rsa, ssh-ed25519, ecdsa-sha2-, or sk-ssh-.");
      return;
    }
    void mutateSshKey(trimmed);
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
          <CardDescription>Update your email address.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleEmailSubmit} className="space-y-4">
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
            <Button type="submit" disabled={emailLoading}>
              {emailLoading ? "Saving..." : "Save"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>SSH Public Key</CardTitle>
          <CardDescription>
            Paste your SSH public key to connect to sessions via VS Code Remote - SSH.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSshKeySubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="ssh-key">Public Key</Label>
              <Textarea
                id="ssh-key"
                placeholder="ssh-ed25519 AAAA..."
                value={sshKey}
                onChange={(e) => {
                  setSshKey(e.target.value);
                  setSshKeyError(null);
                }}
                rows={4}
                className="font-mono text-xs"
              />
              {sshKeyError ? (
                <p className="text-sm text-destructive">{sshKeyError}</p>
              ) : null}
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={sshKeyLoading}>
                {sshKeyLoading ? "Saving..." : "Save SSH Key"}
              </Button>
              {user?.ssh_public_key ? (
                <Button
                  type="button"
                  variant="outline"
                  disabled={sshKeyLoading}
                  onClick={() => {
                    setSshKey("");
                    void mutateSshKey(null);
                  }}
                >
                  Remove Key
                </Button>
              ) : null}
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
