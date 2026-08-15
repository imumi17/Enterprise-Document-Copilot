import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { buttonVariants } from "@/components/ui/button";
import { api, type CurrentUser } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/http";

export function HomePage() {
  const { session } = useAuth();
  const [profile, setProfile] = useState<CurrentUser | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) {
      setProfile(null);
      setProfileError(null);
      return;
    }

    api
      .getMe()
      .then(setProfile)
      .catch((error: unknown) => {
        if (error instanceof ApiError) {
          setProfileError(error.message);
          return;
        }
        setProfileError("Could not load your profile.");
      });
  }, [session]);

  return (
    <section className="space-y-4">
      <h1 className="text-3xl font-semibold tracking-tight">
        Driftwood research intake, grounded in filings
      </h1>
      <p className="max-w-2xl text-muted-foreground">
        Ask questions across curated SEC filings and get cited answers backed by
        source passages.
      </p>

      {session ? (
        <div className="rounded-lg border border-border bg-card p-4 text-sm">
          <p className="font-medium">Signed in as {session.user.email}</p>
          {profile ? (
            <p className="mt-1 text-muted-foreground">
              Backend profile confirmed for user id{" "}
              <code className="text-xs">{profile.id}</code>
            </p>
          ) : null}
          {profileError ? (
            <p className="mt-1 text-destructive">{profileError}</p>
          ) : null}
          <Link to="/chat" className={buttonVariants()}>
            Open chat
          </Link>
        </div>
      ) : (
        <Link to="/login" className={buttonVariants()}>
          Sign in to continue
        </Link>
      )}
    </section>
  );
}
