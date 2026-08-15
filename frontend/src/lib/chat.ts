import { ApiError } from "@/lib/http";
import { env } from "@/lib/env";

export function formatApiError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.isNetworkError) {
      return `Could not reach the API at ${env.apiBaseUrl}. Check that the backend is running and CORS is configured.`;
    }
    if (error.status === 401) {
      return "Your session expired. Please sign in again.";
    }
    if (error.status === 403) {
      return "You do not have access to this resource.";
    }
    if (error.status === 404) {
      return "That chat thread could not be found.";
    }
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Something went wrong. Please try again.";
}

export function formatChatStreamError(error: unknown): string {
  if (error instanceof Error) {
    const lowered = error.message.toLowerCase();
    if (lowered.includes("failed to fetch") || lowered.includes("network")) {
      return `Connection failed. Is the backend running at ${env.apiBaseUrl}?`;
    }
    return error.message;
  }
  return "The assistant could not complete that request.";
}

export function isInsufficientEvidenceText(text: string): boolean {
  const lowered = text.toLowerCase();
  return (
    lowered.includes("does not contain enough") ||
    lowered.includes("not contain enough") ||
    lowered.includes("insufficient evidence") ||
    lowered.includes("not enough information") ||
    lowered.includes("could not find") ||
    lowered.includes("couldn't find")
  );
}

export function isGroundingFailureMessage(
  text: string,
  metadata?: MessageMetadata,
): boolean {
  if (metadata?.grounding_failed) {
    return true;
  }
  return text.includes("couldn't verify the citations");
}

export type StoredCitation = {
  label: string;
  chunk_id: string;
  excerpt: string;
  ticker?: string;
  company_name?: string;
  filing_type?: string;
  filing_date?: string;
  fiscal_year?: number;
  section?: string | null;
  page?: number | null;
  source_url?: string;
  accession_number?: string;
  chunk_index?: number;
};

export type MessageMetadata = {
  citations?: StoredCitation[];
  usage?: {
    input_tokens?: number;
    output_tokens?: number;
    model?: string | null;
  };
  grounding_failed?: boolean;
};

export function getMessageMetadata(message: {
  metadata?: MessageMetadata;
}): MessageMetadata | undefined {
  return message.metadata;
}

export function formatFilingDate(value: string | undefined): string {
  if (!value) {
    return "Unknown date";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(parsed);
}
