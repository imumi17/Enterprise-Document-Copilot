import { env } from "@/lib/env";
import { getAccessToken } from "@/lib/supabase";

const DEFAULT_TIMEOUT_MS = 30_000;

export class ApiError extends Error {
  readonly status: number;
  readonly isNetworkError: boolean;
  readonly body: unknown;

  constructor(
    message: string,
    status: number,
    isNetworkError: boolean,
    body: unknown = undefined,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.isNetworkError = isNetworkError;
    this.body = body;
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  auth?: boolean;
  timeoutMs?: number;
};

async function parseResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

function buildUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `${env.apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const {
    auth = true,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    body,
    headers,
    ...rest
  } = options;

  const requestHeaders = new Headers(headers);
  if (body !== undefined) {
    requestHeaders.set("Content-Type", "application/json");
  }

  if (auth) {
    const token = await getAccessToken();
    if (!token) {
      throw new ApiError("Not authenticated", 401, false);
    }
    requestHeaders.set("Authorization", `Bearer ${token}`);
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(buildUrl(path), {
      ...rest,
      headers: requestHeaders,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });

    const responseBody = await parseResponseBody(response);
    if (!response.ok) {
      const message =
        typeof responseBody === "object" &&
        responseBody !== null &&
        "detail" in responseBody &&
        typeof responseBody.detail === "string"
          ? responseBody.detail
          : `Request failed with status ${response.status}`;

      throw new ApiError(message, response.status, false, responseBody);
    }

    return responseBody as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("Request timed out", 0, true);
    }
    throw new ApiError(
      error instanceof Error ? error.message : "Network request failed",
      0,
      true,
    );
  } finally {
    clearTimeout(timeout);
  }
}

export const http = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "POST", body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PUT", body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PATCH", body }),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "DELETE" }),
};
