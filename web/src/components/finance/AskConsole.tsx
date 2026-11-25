import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  Alert,
  Badge,
  Button,
  EmptyState,
  Panel,
  Skeleton,
  TextArea,
} from "../ui";
import { runAgents } from "../../lib/api";
import type { AgentRunResponse, ApiError } from "../../lib/types";
import { AgentTrace } from "./AgentTrace";
import { LineageMeta } from "./LineageMeta";

const EXAMPLES = [
  {
    short: "Reconcile samples",
    question: "Reconcile sample_bank against sample_ledger",
  },
  {
    short: "Budget variance",
    question: "Show budget variance for sample_actuals vs sample_budget",
  },
  {
    short: "What can you run?",
    question: "What workflows can you run?",
  },
] as const;

export function AskConsole() {
  const [question, setQuestion] = useState<string>(EXAMPLES[0].question);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentRunResponse | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const liveRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q) {
      setError("Enter a question before running the agent pipeline.");
      return;
    }
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);
    setError(null);
    try {
      const data = await runAgents(q, undefined, ac.signal);
      setResult(data);
      liveRef.current?.focus();
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      const apiErr = err as ApiError;
      setError(
        apiErr.message ||
          "Could not reach the agent API. Is the backend running on :8000?",
      );
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  function cancel() {
    abortRef.current?.abort();
    setLoading(false);
  }

  return (
    <Panel
      id="ask-console"
      title="Agent console"
      description="Router → Optimizer → Specialist → Reviewer → Narrator. Numbers come from deterministic workflows only."
    >
      <form className="gf-stack" onSubmit={onSubmit} noValidate>
        <TextArea
          label="Question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          hint="Ask in plain language. Sample aliases: sample_bank, sample_ledger, sample_actuals, sample_budget."
          error={
            error && !question.trim()
              ? "Question is required"
              : undefined
          }
          required
          disabled={loading}
          rows={3}
        />
        <div className="gf-chips" role="group" aria-label="Example prompts">
          {EXAMPLES.map((ex) => (
            <Button
              key={ex.question}
              type="button"
              variant="ghost"
              size="sm"
              chip
              disabled={loading}
              title={ex.question}
              onClick={() => setQuestion(ex.question)}
            >
              {ex.short}
            </Button>
          ))}
        </div>
        <div className="gf-row gf-row--actions">
          <Button type="submit" loading={loading} disabled={!question.trim()}>
            Run agents
          </Button>
          {loading ? (
            <Button type="button" variant="secondary" onClick={cancel}>
              Cancel
            </Button>
          ) : null}
        </div>
      </form>

      {error && question.trim() ? (
        <div style={{ marginTop: "1.25rem" }}>
          <Alert
            tone="error"
            title="Request failed"
            onDismiss={() => setError(null)}
          >
            {error}
          </Alert>
        </div>
      ) : null}

      <div
        ref={liveRef}
        tabIndex={-1}
        style={{ marginTop: "1.5rem", outline: "none" }}
        aria-live="polite"
      >
        {loading ? (
          <div className="gf-stack">
            <Skeleton height="1.25rem" width="40%" label="Loading answer" />
            <Skeleton height="4rem" />
            <AgentTrace steps={[]} loading />
          </div>
        ) : null}

        {!loading && !result && !error ? (
          <EmptyState
            title="No run yet"
            description="Submit a question to see the agent trace, lineage, and governed answer."
          />
        ) : null}

        {!loading && result ? (
          <div className="gf-stack gf-rise">
            <div className="gf-row">
              <Badge tone="info">{result.intent || "unknown intent"}</Badge>
              <LineageMeta
                lineage={result.lineage}
                runId={result.run_id}
                cacheHit={result.cache_hit}
              />
            </div>
            <p style={{ margin: 0, fontSize: "1.05rem" }}>{result.answer}</p>
            {result.review && Object.keys(result.review).length > 0 ? (
              <Alert
                tone={
                  String(result.review.status || "")
                    .toLowerCase()
                    .includes("fail")
                    ? "warning"
                    : "success"
                }
                title="Reviewer"
              >
                <pre className="gf-json" style={{ maxHeight: "8rem" }}>
                  {JSON.stringify(result.review, null, 2)}
                </pre>
              </Alert>
            ) : null}
            <AgentTrace steps={result.trace || []} />
            {result.result ? (
              <details>
                <summary style={{ cursor: "pointer", color: "var(--gf-mist)" }}>
                  Workflow payload
                </summary>
                <pre className="gf-json">
                  {JSON.stringify(result.result, null, 2)}
                </pre>
              </details>
            ) : null}
          </div>
        ) : null}
      </div>
    </Panel>
  );
}
