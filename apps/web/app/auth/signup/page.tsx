"use client";

import { useState } from "react";
import { apiPostJson, type AuthUser } from "../../../lib/api";

export default function SignupPage(): JSX.Element {
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
    <section className="card" style={{ maxWidth: 420 }}>
      <h1>Sign up</h1>
      <form onSubmit={handleSubmit} className="grid" style={{ gap: 10 }}>
        <div>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
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
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            minLength={8}
          />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? "Creating..." : "Create account"}
        </button>
      </form>
      {error ? <p className="muted" style={{ color: "#a11" }}>{error}</p> : null}
      {message ? <p className="muted">{message}</p> : null}
    </section>
  );
}
