"use client";

import { useState } from "react";

import { apiPostJson, type AuthUser } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";

export default function SignupPage(): React.JSX.Element {
  const [email, setEmail] = useState("you@example.com");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    setError("");

    try {
      const user = await apiPostJson<AuthUser>("/api/auth/signup", { email, password });
      setMessage(`Account created for ${user.email}.`);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Sign up failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex justify-center">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl">Sign up</CardTitle>
          <CardDescription>Create a new MedForge account</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4" data-testid="signup-form">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                data-testid="signup-email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                data-testid="signup-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                minLength={8}
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading} data-testid="signup-submit">
              {loading ? "Creating..." : "Create account"}
            </Button>
          </form>

          {error ? (
            <Alert variant="destructive" className="mt-4" data-testid="signup-error">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}

          {message ? (
            <Alert className="mt-4" data-testid="signup-success">
              <AlertDescription>{message}</AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
