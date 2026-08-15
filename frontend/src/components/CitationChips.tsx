import type { StoredCitation } from "@/lib/chat";

type CitationChipsProps = {
  citations: StoredCitation[];
  selectedChunkId: string | null;
  onSelect: (chunkId: string) => void;
};

export function CitationChips({
  citations,
  selectedChunkId,
  onSelect,
}: CitationChipsProps) {
  if (citations.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-1.5 pt-2">
      {citations.map((citation) => {
        const selected = citation.chunk_id === selectedChunkId;
        return (
          <button
            key={citation.chunk_id}
            type="button"
            onClick={() => onSelect(citation.chunk_id)}
            className={
              selected
                ? "rounded-full border border-primary bg-primary px-2.5 py-0.5 text-xs font-medium text-primary-foreground"
                : "rounded-full border border-border bg-background px-2.5 py-0.5 text-xs font-medium text-foreground hover:bg-muted"
            }
          >
            {citation.label}
            {citation.ticker ? ` · ${citation.ticker}` : ""}
          </button>
        );
      })}
    </div>
  );
}
