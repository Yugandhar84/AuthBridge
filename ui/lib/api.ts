// The UI calls the local services through Next.js rewrites (next.config.mjs).
export const provider = (path: string) => `/svc/provider${path}`;
export const payer = (path: string) => `/svc/payer${path}`;

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

async function handle<T>(res: Response): Promise<T> {
  const text = await res.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!res.ok) {
    const b = body as { detail?: string; issue?: { diagnostics?: string }[] } | string | null;
    const msg =
      typeof b === "string"
        ? b
        : b?.detail || b?.issue?.[0]?.diagnostics || `Request failed (${res.status})`;
    throw new ApiError(msg, res.status);
  }
  return body as T;
}

export async function get<T>(url: string): Promise<T> {
  return handle<T>(await fetch(url, { cache: "no-store" }));
}

export async function send<T>(url: string, body?: unknown, method = "POST"): Promise<T> {
  return handle<T>(
    await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  );
}

export type AgentEvent =
  | { type: "text"; text: string }
  | { type: "status"; message: string }
  | { type: "table"; result_set: { columns?: string[]; rows?: unknown[][]; [k: string]: unknown } }
  | { type: "chart"; spec: unknown }
  | { type: "annotation"; annotation: unknown }
  | { type: "error"; message: string }
  | { type: "done" };

/** POST to an agent endpoint and yield simplified SSE events. */
export async function* streamAgent(url: string, body: unknown): AsyncGenerator<AgentEvent> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) {
    yield { type: "error", message: `Agent request failed (${res.status})` };
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const chunk = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const line = chunk.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      try {
        yield JSON.parse(line.slice(5).trim()) as AgentEvent;
      } catch {
        /* ignore malformed event */
      }
    }
  }
}
