import { http } from "@/lib/http";

export type CurrentUser = {
  id: string;
  email: string;
};

export type ChatThread = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type UiMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  parts: Array<{ type: string; text?: string }>;
  metadata?: {
    citations?: Array<{
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
    }>;
    usage?: {
      input_tokens?: number;
      output_tokens?: number;
      model?: string | null;
    };
    grounding_failed?: boolean;
  };
};

export const api = {
  getMe: () => http.get<CurrentUser>("/me"),
  listThreads: () => http.get<ChatThread[]>("/chat/threads"),
  createThread: () => http.post<ChatThread>("/chat/threads"),
  getThreadMessages: (threadId: string) =>
    http.get<{ messages: UiMessage[] }>(`/chat/threads/${threadId}/messages`),
};
