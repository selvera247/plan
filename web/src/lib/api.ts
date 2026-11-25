import type {
  AgentRunResponse,
  ApiError,
  WorkflowResponse,
} from "./types";

const API_KEY = import.meta.env.VITE_API_KEY as string | undefined;

function headers(json = true): HeadersInit {
  const h: Record<string, string> = {};
  if (json) h["Content-Type"] = "application/json";
  if (API_KEY) h["X-API-Key"] = API_KEY;
  return h;
}

async function parseError(res: Response): Promise<ApiError> {
  let message = res.statusText || "Request failed";
  let detail: string | undefined;
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") {
      message = body.detail;
    } else if (typeof body?.error === "string") {
      message = body.error;
      detail = body.detail;
    } else if (body?.detail) {
      message = JSON.stringify(body.detail);
    }
  } catch {
    /* ignore non-JSON */
  }
  return { status: res.status, message, detail };
}

export async function runAgents(
  question: string,
  conversationId?: string,
  signal?: AbortSignal,
): Promise<AgentRunResponse> {
  const res = await fetch("/v1/agents/run", {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({
      question,
      conversation_id: conversationId || null,
    }),
    signal,
  });
  if (!res.ok) throw await parseError(res);
  return res.json();
}

export async function runReconcile(
  body: {
    left_source: string;
    right_source: string;
    amount_tolerance: number;
    include_details: boolean;
  },
  signal?: AbortSignal,
): Promise<WorkflowResponse> {
  const res = await fetch("/v1/workflows/reconcile", {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) throw await parseError(res);
  return res.json();
}

export async function runVariance(
  body: {
    actuals_source: string;
    budget_source: string;
    threshold_pct: number;
    threshold_abs: number | null;
    include_details: boolean;
  },
  signal?: AbortSignal,
): Promise<WorkflowResponse> {
  const res = await fetch("/v1/workflows/variance", {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) throw await parseError(res);
  return res.json();
}

export async function checkHealth(
  signal?: AbortSignal,
): Promise<{ ok: boolean; status: string }> {
  try {
    const res = await fetch("/health", { signal });
    if (!res.ok) return { ok: false, status: `HTTP ${res.status}` };
    const data = await res.json();
    return { ok: data.status === "ok" || data.status === "healthy", status: data.status };
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    return { ok: false, status: "unreachable" };
  }
}
