type ChatStatusIndicatorProps = {
  label: string;
};

export function ChatStatusIndicator({ label }: ChatStatusIndicatorProps) {
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <span className="flex gap-1">
        <span className="size-1.5 animate-pulse rounded-full bg-muted-foreground" />
        <span className="size-1.5 animate-pulse rounded-full bg-muted-foreground [animation-delay:150ms]" />
        <span className="size-1.5 animate-pulse rounded-full bg-muted-foreground [animation-delay:300ms]" />
      </span>
      <span>{label}</span>
    </div>
  );
}
