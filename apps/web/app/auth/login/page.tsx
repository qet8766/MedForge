"use client";

import { useState } from "react";
import { apiPostJson, type AuthUser } from "../../../lib/api";

export default function LoginPage(): React.JSX.Element {
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
      const user = await apiPostJson<AuthUser>("/api/auth/login", { email, password });
      setMessage(`Signed in as ${user.email}.`);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Sign in failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card" style={{ maxWidth: 420 }}>
      <h1>Login</h1>
      <form onSubmit={handleSubmit} className="grid" style={{ gap: 10 }} data-testid="login-form">
        <div>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            data-testid="login-email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            data-testid="login-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            minLength={8}
          />
        </div>
        <button type="submit" disabled={loading} data-testid="login-submit">
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
      {error ? <p className="muted" style={{ color: "#a11" }} data-testid="login-error">{error}</p> : null}
      {message ? <p className="muted" data-testid="login-success">{message}</p> : null}
    </section>
  );
}
