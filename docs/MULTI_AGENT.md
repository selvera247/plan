# Multi-Agent Workflow (Governed Finance)

Four collaborating agents own the question → answer path. Numbers still come only from deterministic domain workflows.

```
┌─────────────┐
│   Router    │  Architect-style: classify intent, pick specialist + default args
└──────┬──────┘
       ▼
┌─────────────┐
│  Optimizer  │  Tune args (include_details, thresholds) for cost/latency
└──────┬──────┘
       ▼
┌─────────────┐
│ Specialist  │  Engineer-style: ReconcileAgent | VarianceAgent → WorkflowService
└──────┬──────┘
       ▼
┌─────────────┐
│  Reviewer   │  Quality gate: tool, lineage, required numeric fields
└──────┬──────┘
       ▼
┌─────────────┐
│  Narrator   │  Template (offline) or OpenAI (optional) — cites lineage only
└─────────────┘
```

## Agent responsibilities

| Agent | Role analogue | Responsibility |
|-------|---------------|----------------|
| `RouterAgent` | Architect | Intent detection (`reconcile` / `variance` / `unknown`) + default tool args |
| `OptimizerAgent` | Optimizer | Prefer summary mode for overview questions; keep details when asked |
| `ReconcileAgent` / `VarianceAgent` | Engineer | Call `WorkflowService` (cache + audit) |
| `ReviewerAgent` | Reviewer | Fail closed if lineage missing or expected fields absent |
| `Orchestrator` | Conductor | Run pipeline, attach agent trace for auditability |

## Offline-first

Routing and narration work **without** `OPENAI_API_KEY` via deterministic rules/templates so CI and home-lab demos stay reliable. When a key is present, the narrator may optionally polish wording — still without inventing numbers.

## API

`POST /v1/agents/run` — `{ "question": "..." }` → answer + lineage + agent_trace.
