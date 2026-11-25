import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  Alert,
  Button,
  EmptyState,
  Panel,
  SelectField,
  Skeleton,
  TextField,
} from "../ui";
import { runReconcile, runVariance } from "../../lib/api";
import type { ApiError, WorkflowResponse } from "../../lib/types";
import { LineageMeta } from "./LineageMeta";
import { MetricStrip } from "./MetricStrip";

type Mode = "reconcile" | "variance";

function metricsFrom(mode: Mode, result: Record<string, unknown>) {
  const totals =
    result.totals && typeof result.totals === "object"
      ? (result.totals as Record<string, unknown>)
      : {};

  if (mode === "reconcile") {
    const variance = totals.total_variance ?? result.total_variance;
    return [
      { label: "Matched", value: String(result.matched_count ?? "—") },
      { label: "Unmatched L", value: String(result.unmatched_left_count ?? "—") },
      { label: "Unmatched R", value: String(result.unmatched_right_count ?? "—") },
      {
        label: "Variance",
        value: variance != null ? Number(variance).toFixed(2) : "—",
      },
    ];
  }

  const flagged =
    result.flagged_count ??
    (Array.isArray(result.flagged) ? result.flagged.length : undefined);
  const accounts =
    result.item_count ??
    result.account_count ??
    (Array.isArray(result.accounts) ? result.accounts.length : undefined);
  const varPct =
    totals.percent_variance ??
    result.total_variance_pct ??
    result.variance_pct;

  return [
    { label: "Accounts", value: String(accounts ?? "—") },
    { label: "Flagged", value: String(flagged ?? "—") },
    {
      label: "Total var %",
      value: varPct != null ? `${Number(varPct).toFixed(2)}%` : "—",
    },
  ];
}

export function WorkflowPanel() {
  const [mode, setMode] = useState<Mode>("reconcile");
  const [left, setLeft] = useState("sample_bank");
  const [right, setRight] = useState("sample_ledger");
  const [tolerance, setTolerance] = useState("0.01");
  const [threshold, setThreshold] = useState("5");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [data, setData] = useState<WorkflowResponse | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  useEffect(() => {
    if (mode === "reconcile") {
      setLeft("sample_bank");
      setRight("sample_ledger");
    } else {
      setLeft("sample_actuals");
      setRight("sample_budget");
    }
    setData(null);
    setError(null);
    setFieldErrors({});
  }, [mode]);

  function validate(): boolean {
    const errs: Record<string, string> = {};
    if (!left.trim()) errs.left = "Source is required";
    if (!right.trim()) errs.right = "Source is required";
    if (mode === "reconcile") {
      const t = Number(tolerance);
      if (!Number.isFinite(t) || t < 0) {
        errs.tolerance = "Must be a non-negative number";
      }
    } else {
      const t = Number(threshold);
      if (!Number.isFinite(t) || t < 0) {
        errs.threshold = "Must be a non-negative number";
      }
    }
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validate()) return;
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);
    setError(null);
    try {
      const res =
        mode === "reconcile"
          ? await runReconcile(
              {
                left_source: left.trim(),
                right_source: right.trim(),
                amount_tolerance: Number(tolerance),
                include_details: false,
              },
              ac.signal,
            )
          : await runVariance(
              {
                actuals_source: left.trim(),
                budget_source: right.trim(),
                threshold_pct: Number(threshold),
                threshold_abs: null,
                include_details: false,
              },
              ac.signal,
            );
      setData(res);
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      const apiErr = err as ApiError;
      setError(apiErr.message || "Workflow request failed");
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Panel
      id="workflows"
      title="Workflow runner"
      description="Call governed reconcile / variance endpoints directly. Summary mode omits large detail arrays."
    >
      <form className="gf-stack" onSubmit={onSubmit} noValidate>
        <SelectField
          label="Workflow"
          value={mode}
          onChange={(e) => setMode(e.target.value as Mode)}
          options={[
            { value: "reconcile", label: "Reconcile" },
            { value: "variance", label: "Budget variance" },
          ]}
          disabled={loading}
        />
        <TextField
          label={mode === "reconcile" ? "Left source" : "Actuals source"}
          value={left}
          onChange={(e) => setLeft(e.target.value)}
          error={fieldErrors.left}
          required
          disabled={loading}
        />
        <TextField
          label={mode === "reconcile" ? "Right source" : "Budget source"}
          value={right}
          onChange={(e) => setRight(e.target.value)}
          error={fieldErrors.right}
          required
          disabled={loading}
        />
        {mode === "reconcile" ? (
          <TextField
            label="Amount tolerance"
            inputMode="decimal"
            value={tolerance}
            onChange={(e) => setTolerance(e.target.value)}
            error={fieldErrors.tolerance}
            hint="Absolute amount difference allowed when matching."
            disabled={loading}
          />
        ) : (
          <TextField
            label="Threshold %"
            inputMode="decimal"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
            error={fieldErrors.threshold}
            hint="Flag accounts whose variance % exceeds this."
            disabled={loading}
          />
        )}
        <div className="gf-row gf-row--actions">
          <Button type="submit" loading={loading} variant="secondary">
            Run workflow
          </Button>
        </div>
      </form>

      {error ? (
        <div style={{ marginTop: "1.25rem" }}>
          <Alert tone="error" title="Workflow failed" onDismiss={() => setError(null)}>
            {error}
          </Alert>
        </div>
      ) : null}

      <div style={{ marginTop: "1.5rem" }} aria-live="polite">
        {loading ? (
          <div className="gf-stack">
            <Skeleton height="2.5rem" />
            <Skeleton height="5rem" />
          </div>
        ) : null}
        {!loading && !data && !error ? (
          <EmptyState
            title="Waiting for a run"
            description="Pick sources and run a workflow to inspect lineage and summary metrics."
          />
        ) : null}
        {!loading && data ? (
          <div className="gf-stack gf-rise">
            <LineageMeta
              lineage={data.lineage}
              runId={data.run_id}
              cacheHit={data.cache_hit}
              durationMs={data.duration_ms}
            />
            <MetricStrip metrics={metricsFrom(mode, data.result || {})} />
            <details>
              <summary style={{ cursor: "pointer", color: "var(--gf-mist)" }}>
                Full result JSON
              </summary>
              <pre className="gf-json">
                {JSON.stringify(data.result, null, 2)}
              </pre>
            </details>
          </div>
        ) : null}
      </div>
    </Panel>
  );
}
