import { type FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { supabase } from "@/lib/supabase";

type AuthMode = "sign-in" | "sign-up";

export function LoginPage() {
  const navigate = useNavigate();
  const { session } = useAuth();
  const [mode, setMode] = useState<AuthMode>("sign-in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (session) {
    return <Navigate to="/chat" replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    const credentials = { email: email.trim(), password };

    const result =
      mode === "sign-in"
        ? await supabase.auth.signInWithPassword(credentials)
        : await supabase.auth.signUp(credentials);

    setSubmitting(false);

    if (result.error) {
      setError(result.error.message);
      return;
    }

    if (mode === "sign-up" && !result.data.session) {
      setError(
        "Account created. If email confirmation is enabled in Supabase, confirm your email before signing in.",
      );
      return;
    }

    navigate("/chat", { replace: true });
  }

  return (
    <section className="mx-auto max-w-md space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">
          {mode === "sign-in" ? "Sign in" : "Create account"}
        </h1>
        <p className="text-sm text-muted-foreground">
          Use your Driftwood email address. Access is limited to authenticated
          analysts.
        </p>
      </div>

      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            minLength={8}
            autoComplete={
              mode === "sign-in" ? "current-password" : "new-password"
            }
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </div>

        {error ? (
          <p className="text-sm text-destructive" role="alert">{error}</p>
        ) : null}

        <Button type="submit" disabled={submitting} className="w-full">
          {submitting
            ? "Working…"
            : mode === "sign-in"
              ? "Sign in"
              : "Create account"}
        </Button>
      </form>

      <p className="text-sm text-muted-foreground">
        {mode === "sign-in" ? "Need an account?" : "Already have an account?"}
        <button
          type="button"
          className="ml-1 font-medium text-foreground underline-offset-4 hover:underline"
          onClick={() =>
            setMode((current) =>
              current === "sign-in" ? "sign-up" : "sign-in",
            )
          }
        >
          {mode === "sign-in" ? "Create one" : "Sign in"}
        </button>
      </p>

      <p className="text-sm text-muted-foreground">
        <Link to="/" className="underline-offset-4 hover:underline">
          Back to home
        </Link>
      </p>
    </section>
  );
}
