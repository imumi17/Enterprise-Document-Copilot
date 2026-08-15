import { Link, Outlet } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

export function AppLayout() {
  const { session, user, loading, signOut } = useAuth();

  return (
    <div className="min-h-svh bg-background text-foreground">
      <header className="border-b border-border px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
          <span className="text-lg font-semibold tracking-tight">
            Document Copilot
          </span>
          <nav className="flex items-center gap-4 text-sm text-muted-foreground">
            <Link to="/" className="hover:text-foreground">Home</Link>
            {session ? (
              <>
                <Link to="/chat" className="hover:text-foreground">Chat</Link>
                <span className="hidden text-foreground sm:inline">
                  {user?.email}
                </span>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => signOut()}
                  disabled={loading}
                >
                  Sign out
                </Button>
              </>
            ) : (
              <Link to="/login" className="hover:text-foreground">Login</Link>
            )}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
