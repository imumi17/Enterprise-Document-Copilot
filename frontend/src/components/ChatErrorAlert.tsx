import { formatApiError, formatChatStreamError } from "@/lib/chat";

type ChatErrorAlertProps = {
  error: unknown;
  variant?: "api" | "stream";
};

export function ChatErrorAlert({ error, variant = "api" }: ChatErrorAlertProps) {
  const message =
    variant === "stream" ? formatChatStreamError(error) : formatApiError(error);

  return (
    <div
      role="alert"
      className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
    >
      {message}
    </div>
  );
}
