import { Badge } from "../ui";
import type { AgentTraceStep } from "../../lib/types";

export type AgentTraceProps = {
  steps: AgentTraceStep[];
  loading?: boolean;
};

function stepTone(status?: string): "ok" | "warn" | "danger" | "neutral" {
  const s = (status || "").toLowerCase();
  if (s.includes("pass") || s.includes("ok") || s.includes("done")) return "ok";
  if (s.includes("warn") || s.includes("review")) return "warn";
  if (s.includes("fail") || s.includes("error") || s.includes("reject"))
    return "danger";
  return "neutral";
}

function summarize(step: AgentTraceStep): string | null {
  if (typeof step.message === "string" && step.message.trim()) {
    return step.message;
  }
  const detail = step.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (detail && typeof detail === "object") {
    const d = detail as Record<string, unknown>;
    if (typeof d.rationale === "string") return d.rationale;
    if (typeof d.choice === "string") return d.choice;
    if (typeof d.intent === "string") {
      return `intent: ${d.intent}${d.specialist ? ` → ${String(d.specialist)}` : ""}`;
    }
    if (typeof d.summary === "string") return d.summary;
    try {
      return JSON.stringify(detail);
    } catch {
      return null;
    }
  }
  if (step.intent != null) return `intent: ${String(step.intent)}`;
  if (step.summary != null && typeof step.summary !== "object") {
    return String(step.summary);
  }
  return null;
}

export function AgentTrace({ steps, loading }: AgentTraceProps) {
  if (loading) {
    return (
      <ol className="gf-trace" aria-busy="true" aria-label="Agent pipeline">
        {["Router", "Optimizer", "Specialist", "Reviewer", "Narrator"].map(
          (role) => (
            <li key={role} className="gf-trace__step gf-trace__step--active">
              <span className="gf-trace__role">{role}</span>
              <span className="gf-muted">Waiting…</span>
            </li>
          ),
        )}
      </ol>
    );
  }

  if (!steps.length) {
    return null;
  }

  return (
    <ol className="gf-trace" aria-label="Agent pipeline">
      {steps.map((step, i) => {
        const role = String(step.agent || step.role || `step-${i + 1}`).replace(
          /_/g,
          " ",
        );
        const status = step.status ? String(step.status) : undefined;
        const body = summarize(step);
        return (
          <li
            key={`${role}-${i}`}
            className="gf-trace__step gf-trace__step--active"
          >
            <div>
              <div className="gf-trace__role">{role}</div>
              {status ? (
                <Badge tone={stepTone(status)} className="gf-mono">
                  {status}
                </Badge>
              ) : null}
            </div>
            <div>
              {body ? (
                <p
                  style={{ margin: 0 }}
                  className={
                    body.startsWith("{") || body.startsWith("[")
                      ? "gf-mono"
                      : undefined
                  }
                >
                  {body.length > 220 ? `${body.slice(0, 218)}…` : body}
                </p>
              ) : (
                <p style={{ margin: 0 }} className="gf-muted">
                  —
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
