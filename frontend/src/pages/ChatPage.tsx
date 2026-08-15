import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport, type UIMessage } from "ai";
import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { CitationChips } from "@/components/CitationChips";
import { ChatErrorAlert } from "@/components/ChatErrorAlert";
import { ChatStatusIndicator } from "@/components/ChatStatusIndicator";
import { SourcePassagePanel } from "@/components/SourcePassagePanel";
import { Button } from "@/components/ui/button";
import { api, type ChatThread, type UiMessage } from "@/lib/api";
import {
  getMessageMetadata,
  isGroundingFailureMessage,
  isInsufficientEvidenceText,
  type StoredCitation,
} from "@/lib/chat";
import { env } from "@/lib/env";
import { getAccessToken } from "@/lib/supabase";

const EXAMPLE_QUESTIONS = [
  "What did NVIDIA disclose about data center revenue?",
  "What are Apple's main risk factors in the latest 10-K?",
  "How did Amazon describe AWS segment performance?",
];

function getMessageText(
  message: { parts: Array<{ type: string; text?: string }> },
): string {
  return message.parts
    .filter((part) => part.type === "text")
    .map((part) => ("text" in part ? part.text : ""))
    .join("");
}

function AssistantMessage({
  message,
  selectedChunkId,
  onSelectCitation,
}: {
  message: UiMessage;
  selectedChunkId: string | null;
  onSelectCitation: (chunkId: string) => void;
}) {
  const text = getMessageText(message);
  const metadata = getMessageMetadata(message);
  const citations = metadata?.citations ?? [];
  const groundingFailed = isGroundingFailureMessage(text, metadata);
  const insufficientEvidence = isInsufficientEvidenceText(text);

  return (
    <div className="mr-auto max-w-[85%] space-y-1 rounded-lg bg-muted px-3 py-2 text-sm text-foreground">
      <p>{text}</p>

      {groundingFailed ? (
        <p className="text-xs text-destructive">
          Grounding check failed — citations could not be verified.
        </p>
      ) : null}

      {insufficientEvidence ? (
        <p className="text-xs text-muted-foreground">
          No matching passages were found in the ingested filing corpus for this question.
        </p>
      ) : null}

      <CitationChips
        citations={citations}
        selectedChunkId={selectedChunkId}
        onSelect={onSelectCitation}
      />
    </div>
  );
}

function ChatThreadLoaded({
  threadId,
  initialMessages,
}: {
  threadId: string;
  initialMessages: UiMessage[];
}) {
  const [input, setInput] = useState("");
  const [selectedCitation, setSelectedCitation] = useState<StoredCitation | null>(null);
  const previousStatusRef = useRef<string>("ready");

  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: `${env.apiBaseUrl}/chat/stream`,
        headers: async (): Promise<Record<string, string>> => {
          const token = await getAccessToken();
          if (!token) {
            return {};
          }
          return { Authorization: `Bearer ${token}` };
        },
      }),
    [],
  );

  const { messages, sendMessage, setMessages, status, error } = useChat({
    id: threadId,
    messages: initialMessages as UIMessage[],
    transport,
  });

  useEffect(() => {
    const wasBusy =
      previousStatusRef.current === "streaming" ||
      previousStatusRef.current === "submitted";
    previousStatusRef.current = status;

    if (!wasBusy || status !== "ready") {
      return;
    }

    api
      .getThreadMessages(threadId)
      .then((response) => {
        setMessages(response.messages as UIMessage[]);
      })
      .catch(() => {
        // Keep streamed text if refresh fails.
      });
  }, [status, threadId, setMessages]);

  useEffect(() => {
    const lastAssistant = [...messages]
      .reverse()
      .find((message) => message.role === "assistant");
    if (!lastAssistant) {
      return;
    }

    const metadata = getMessageMetadata(lastAssistant as UiMessage);
    const citations = metadata?.citations ?? [];
    if (citations.length === 0) {
      return;
    }

    const stillValid = citations.some(
      (citation) => citation.chunk_id === selectedCitation?.chunk_id,
    );
    if (!stillValid) {
      setSelectedCitation(citations[0]);
    }
  }, [messages, selectedCitation?.chunk_id]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text || status === "streaming" || status === "submitted") {
      return;
    }

    setInput("");
    setSelectedCitation(null);
    await sendMessage({ text });
  }

  const isBusy = status === "streaming" || status === "submitted";

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
      <div className="flex min-h-[60vh] flex-col gap-4">
        <div className="flex-1 space-y-3 overflow-y-auto rounded-lg border border-border bg-card p-4">
          {messages.length === 0 ? (
            <div className="space-y-3 text-sm text-muted-foreground">
              <p>
                Ask a question about a filing in the corpus. Answers are grounded in
                retrieved SEC passages with citations.
              </p>
              <div className="space-y-1">
                <p className="font-medium text-foreground">Try asking:</p>
                <ul className="list-inside list-disc space-y-1">
                  {EXAMPLE_QUESTIONS.map((question) => (
                    <li key={question}>{question}</li>
                  ))}
                </ul>
              </div>
            </div>
          ) : null}

          {messages.map((message) =>
            message.role === "user" ? (
              <div
                key={message.id}
                className="ml-auto max-w-[85%] rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground"
              >
                {getMessageText(message)}
              </div>
            ) : (
              <AssistantMessage
                key={message.id}
                message={message as UiMessage}
                selectedChunkId={selectedCitation?.chunk_id ?? null}
                onSelectCitation={(chunkId) => {
                  const metadata = getMessageMetadata(message as UiMessage);
                  const citation = metadata?.citations?.find(
                    (item) => item.chunk_id === chunkId,
                  );
                  setSelectedCitation(citation ?? null);
                }}
              />
            ),
          )}

          {isBusy ? (
            <ChatStatusIndicator
              label={
                status === "submitted"
                  ? "Retrieving passages and generating answer…"
                  : "Streaming answer…"
              }
            />
          ) : null}
        </div>

        {error ? <ChatErrorAlert error={error} variant="stream" /> : null}

        <form className="flex gap-2" onSubmit={handleSubmit}>
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask about a 10-K filing…"
            className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
            disabled={isBusy}
          />
          <Button type="submit" disabled={!input.trim() || isBusy}>
            Send
          </Button>
        </form>
      </div>

      <SourcePassagePanel citation={selectedCitation} />
    </div>
  );
}

function ChatThreadPanel({ threadId }: { threadId: string }) {
  const [initialMessages, setInitialMessages] = useState<UiMessage[] | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [historyError, setHistoryError] = useState<unknown>(null);

  useEffect(() => {
    let active = true;
    setLoadingHistory(true);
    setHistoryError(null);

    api
      .getThreadMessages(threadId)
      .then((response) => {
        if (!active) {
          return;
        }
        setInitialMessages(response.messages);
      })
      .catch((loadError: unknown) => {
        if (!active) {
          return;
        }
        setHistoryError(loadError);
      })
      .finally(() => {
        if (active) {
          setLoadingHistory(false);
        }
      });

    return () => {
      active = false;
    };
  }, [threadId]);

  if (loadingHistory || initialMessages === null) {
    return <ChatStatusIndicator label="Loading messages…" />;
  }

  if (historyError) {
    return <ChatErrorAlert error={historyError} />;
  }

  return (
    <ChatThreadLoaded threadId={threadId} initialMessages={initialMessages} />
  );
}

export function ChatPage() {
  const { threadId } = useParams<{ threadId?: string }>();
  const navigate = useNavigate();
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [loadingThreads, setLoadingThreads] = useState(true);
  const [threadsError, setThreadsError] = useState<unknown>(null);

  useEffect(() => {
    let active = true;

    api
      .listThreads()
      .then(async (loadedThreads) => {
        if (!active) {
          return;
        }

        if (!threadId) {
          if (loadedThreads.length > 0) {
            navigate(`/chat/${loadedThreads[0].id}`, { replace: true });
            return;
          }

          const created = await api.createThread();
          if (!active) {
            return;
          }
          navigate(`/chat/${created.id}`, { replace: true });
          return;
        }

        setThreads(loadedThreads);
      })
      .catch((loadError: unknown) => {
        if (!active) {
          return;
        }
        setThreadsError(loadError);
      })
      .finally(() => {
        if (active) {
          setLoadingThreads(false);
        }
      });

    return () => {
      active = false;
    };
  }, [threadId, navigate]);

  async function handleCreateThread() {
    const created = await api.createThread();
    setThreads((current) => [created, ...current]);
    navigate(`/chat/${created.id}`);
  }

  if (loadingThreads) {
    return <ChatStatusIndicator label="Loading chat…" />;
  }

  if (threadsError) {
    return <ChatErrorAlert error={threadsError} />;
  }

  if (!threadId) {
    return <ChatStatusIndicator label="Preparing your chat…" />;
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
      <aside className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">Threads</h2>
          <Button type="button" size="sm" variant="outline" onClick={handleCreateThread}>
            New
          </Button>
        </div>

        {threads.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No threads yet. Start a new chat to query the filing corpus.
          </p>
        ) : (
          <ul className="space-y-1">
            {threads.map((thread) => (
              <li key={thread.id}>
                <Link
                  to={`/chat/${thread.id}`}
                  className={
                    thread.id === threadId
                      ? "block rounded-md bg-muted px-3 py-2 text-sm font-medium"
                      : "block rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-muted"
                  }
                >
                  {thread.title}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </aside>

      <section className="space-y-3">
        <h1 className="text-2xl font-semibold tracking-tight">Chat</h1>
        <ChatThreadPanel threadId={threadId} />
      </section>
    </div>
  );
}
