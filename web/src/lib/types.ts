export type Lineage = {
  workflow?: string;
  version?: string;
  inputs?: Record<string, unknown>;
  [key: string]: unknown;
};

export type AgentTraceStep = {
  agent?: string;
  role?: string;
  status?: string;
  message?: string;
  detail?: string;
  [key: string]: unknown;
};

export type AgentRunResponse = {
  answer: string;
  intent: string;
  lineage: Lineage | null;
  run_id: string | null;
  cache_hit: boolean;
  review: Record<string, unknown>;
  trace: AgentTraceStep[];
  result: Record<string, unknown> | null;
};

export type WorkflowResponse = {
  run_id: string;
  cache_hit: boolean;
  duration_ms: number | null;
  lineage: Lineage | null;
  result: Record<string, unknown>;
};

export type ApiError = {
  status: number;
  message: string;
  detail?: string;
};
