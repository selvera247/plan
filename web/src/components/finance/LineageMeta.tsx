import { Badge } from "../ui";
import type { Lineage } from "../../lib/types";

export type LineageMetaProps = {
  lineage: Lineage | null | undefined;
  runId?: string | null;
  cacheHit?: boolean;
  durationMs?: number | null;
};

export function LineageMeta({
  lineage,
  runId,
  cacheHit,
  durationMs,
}: LineageMetaProps) {
  if (!lineage && !runId) return null;

  return (
    <div className="gf-row" aria-label="Run lineage">
      {lineage?.workflow ? (
        <Badge tone="info" title="Workflow name">
          {String(lineage.workflow)}
          {lineage.version ? ` · v${String(lineage.version)}` : ""}
        </Badge>
      ) : null}
      {runId ? (
        <Badge title="Run id">
          <span className="gf-mono">{runId.slice(0, 8)}…</span>
        </Badge>
      ) : null}
      {typeof cacheHit === "boolean" ? (
        <Badge tone={cacheHit ? "ok" : "neutral"}>
          {cacheHit ? "cache hit" : "fresh"}
        </Badge>
      ) : null}
      {typeof durationMs === "number" ? (
        <Badge>
          <span className="gf-mono">{durationMs.toFixed(1)} ms</span>
        </Badge>
      ) : null}
    </div>
  );
}
