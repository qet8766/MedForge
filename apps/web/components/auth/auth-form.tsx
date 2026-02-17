"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { apiPostJson, type AuthUser } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";

const COPY = {
  login: {
    endpoint: "/api/v2/auth/login",
    title: "Welcome back",
    description: "Sign in to your MedForge account",
    submit: "Sign in",
    submitting: "Signing in...",
    success: (email: string) => `Signed in as ${email}.`,
    errorFallback: "Sign in failed.",
    testId: "login",
    switchText: "Don't have an account?",
    switchLabel: "Sign up",
    switchHref: "/auth/signup",
  },
  signup: {
    endpoint: "/api/v2/auth/signup",
    title: "Create account",
    description: "Get started with MedForge",
    submit: "Create account",
    submitting: "Creating...",
    success: (email: string) => `Account created for ${email}.`,
    errorFallback: "Sign up failed.",
    testId: "signup",
    switchText: "Already have an account?",
    switchLabel: "Log in",
    switchHref: "/auth/login",
  },
} as const;

export function AuthForm({ mode }: { mode: "login" | "signup" }): React.JSX.Element {
  const copy = COPY[mode];
  const router = useRouter();
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
      setTimeout(() => router.push("/sessions"), 600);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : copy.errorFallback);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex w-full justify-center px-4">
      <Card className="w-full max-w-md border-border/50 shadow-lg">
        <CardHeader className="space-y-1 pb-6">
          <CardTitle className="text-2xl font-bold tracking-tight">{copy.title}</CardTitle>
          <CardDescription>{copy.description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
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
            <Button
              type="submit"
              className="w-full"
              disabled={loading}
              data-testid={`${copy.testId}-submit`}
            >
              {loading ? copy.submitting : copy.submit}
            </Button>
          </form>

          {error ? (
            <Alert variant="destructive" data-testid={`${copy.testId}-error`}>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}

          {message ? (
            <Alert data-testid={`${copy.testId}-success`}>
              <AlertDescription>{message}</AlertDescription>
            </Alert>
          ) : null}

          <p className="text-center text-sm text-muted-foreground">
            {copy.switchText}{" "}
            <Link href={copy.switchHref} className="font-medium text-primary hover:underline">
              {copy.switchLabel}
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
