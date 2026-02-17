"use client";

import { useState } from "react";

import { apiPostJson, type AuthUser } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";

const COPY = {
  login: {
    endpoint: "/api/v1/auth/login",
    title: "Login",
    description: "Sign in to your MedForge account",
    submit: "Sign in",
    submitting: "Signing in...",
    success: (email: string) => `Signed in as ${email}.`,
    errorFallback: "Sign in failed.",
    testId: "login",
  },
  signup: {
    endpoint: "/api/v1/auth/signup",
    title: "Sign up",
    description: "Create a new MedForge account",
    submit: "Create account",
    submitting: "Creating...",
    success: (email: string) => `Account created for ${email}.`,
    errorFallback: "Sign up failed.",
    testId: "signup",
  },
} as const;

export function AuthForm({ mode }: { mode: "login" | "signup" }): React.JSX.Element {
  const copy = COPY[mode];

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
      const user = await apiPostJson<AuthUser>(copy.endpoint, { email, password });
      setMessage(copy.success(user.email));
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : copy.errorFallback);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex justify-center">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl">{copy.title}</CardTitle>
          <CardDescription>{copy.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4" data-testid={`${copy.testId}-form`}>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                data-testid={`${copy.testId}-email`}
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
                data-testid={`${copy.testId}-password`}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                minLength={8}
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading} data-testid={`${copy.testId}-submit`}>
              {loading ? copy.submitting : copy.submit}
            </Button>
          </form>

          {error ? (
            <Alert variant="destructive" className="mt-4" data-testid={`${copy.testId}-error`}>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}

          {message ? (
            <Alert className="mt-4" data-testid={`${copy.testId}-success`}>
              <AlertDescription>{message}</AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
