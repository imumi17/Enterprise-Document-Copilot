import type { StoredCitation } from "@/lib/chat";
import { formatFilingDate } from "@/lib/chat";

type SourcePassagePanelProps = {
  citation: StoredCitation | null;
};

export function SourcePassagePanel({ citation }: SourcePassagePanelProps) {
  if (!citation) {
    return (
      <aside className="rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground">
        Select a citation to inspect the source passage from the filing.
      </aside>
    );
  }

  const location =
    citation.section && citation.page
      ? `${citation.section}, page ${citation.page}`
      : citation.section ?? (citation.page ? `Page ${citation.page}` : null);

  return (
    <aside className="space-y-3 rounded-lg border border-border bg-card p-4 text-sm">
      <div className="space-y-1">
        <p className="font-semibold text-foreground">
          {citation.company_name ?? "Source document"}
          {citation.ticker ? ` (${citation.ticker})` : ""}
        </p>
        <p className="text-muted-foreground">
          {citation.filing_type ?? "Filing"}
          {citation.fiscal_year ? ` · FY${citation.fiscal_year}` : ""}
          {citation.filing_date ? ` · ${formatFilingDate(citation.filing_date)}` : ""}
        </p>
        {location ? (
          <p className="text-muted-foreground">{location}</p>
        ) : null}
      </div>

      <blockquote className="rounded-md bg-muted px-3 py-2 text-foreground">
        {citation.excerpt}
      </blockquote>

      {citation.source_url ? (
        <a
          href={citation.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary underline-offset-4 hover:underline"
        >
          View SEC filing
        </a>
      ) : null}
    </aside>
  );
}
