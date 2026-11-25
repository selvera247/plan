# Governed Financial Assistant

A **governed** finance assistant: an OpenAI model answers finance questions by calling **deterministic Python workflows**, never by inventing numbers. Every answer carries **lineage** (workflow name, version, inputs) and can be audited via durable workflow runs.

Design docs: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · [`docs/CLEAN_ARCHITECTURE.md`](docs/CLEAN_ARCHITECTURE.md) · [`docs/MULTI_AGENT.md`](docs/MULTI_AGENT.md).

## Architecture (clean layers)

```
interfaces/ (api · cli · mcp)
        ↓
application/ (use cases + ports)
        ↓
domain/workflows/ (pure reconcile · variance)
        ↑
infrastructure/ (persistence · cache · llm · tools)
```

| Layer | Role |
|-------|------|
| `domain/` | Pure governed workflows (no frameworks) |
| `application/` | Use cases + multi-agent pipeline (Router→Optimizer→Specialist→Reviewer) |
| `infrastructure/` | DB, cache, OpenAI, tool registry, paths |
| `interfaces/` | FastAPI, CLI, MCP adapters |
| `migrations/` · `data/` · `evals/` · `tests/` | Schema, samples, golden evals, regression |

Legacy import paths (`logic/`, `api/`, `services/`, …) remain as **compatibility shims**.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # set OPENAI_API_KEY; optional GOVERNED_API_KEY / DATABASE_URL
```

Requires `OPENAI_API_KEY` for chat. Workflow HTTP endpoints run without it. Optional: `OPENAI_MODEL` (default `gpt-4o-mini`), `GOVERNED_API_KEY`, `DATABASE_URL` (Postgres) or SQLite default.

## Production API

```bash
uvicorn interfaces.api.app:app --reload --port 8000
# or: uvicorn api.app:app
# Docs: http://127.0.0.1:8000/docs
```

Examples:

```bash
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/v1/workflows/reconcile \
  -H 'Content-Type: application/json' \
  -d '{"left_source":"sample_bank","right_source":"sample_ledger"}'
curl -s -X POST http://127.0.0.1:8000/v1/workflows/variance \
  -H 'Content-Type: application/json' \
  -d '{"actuals_source":"sample_actuals","budget_source":"sample_budget"}'

# Multi-agent pipeline (no OpenAI key required)
curl -s -X POST http://127.0.0.1:8000/v1/agents/run \
  -H 'Content-Type: application/json' \
  -d '{"question":"Reconcile sample bank and ledger. How many matched?"}'
```


With auth enabled (`GOVERNED_API_KEY`), send `X-API-Key`.

## Workflows

### 1. Reconciliation — `logic/reconcile.py` v1.0.2

Matches two transaction sets on **amount + date + reference** (configurable amount tolerance). Returns matched/unmatched counts, items, total variance, and lineage.

```python
from logic import reconcile_transactions

result = reconcile_transactions(
    "data/sample_transactions_bank.csv",
    "data/sample_transactions_ledger.csv",
    amount_tolerance=0.01,
)
print(result["matched_count"], result["totals"]["total_variance"], result["lineage"])
```

### 2. Variance analysis — `logic/variance.py` v1.0.2

Compares actuals vs budget by account; flags items above a % (and optional absolute) threshold.

```python
from logic import analyze_variance

result = analyze_variance(
    "data/sample_actuals.csv",
    "data/sample_budget.csv",
    threshold_pct=5.0,
)
print(result["flagged_count"], result["totals"], result["lineage"])
```

## Tool layer

OpenAI function-calling wrappers live in `tools/openai_tools.py`. Each call is logged (stdout + `logs/tool_calls.log`).

Demo source aliases the assistant can use:

| Alias | File |
|-------|------|
| `sample_bank` | `data/sample_transactions_bank.csv` |
| `sample_ledger` | `data/sample_transactions_ledger.csv` |
| `sample_actuals` | `data/sample_actuals.csv` |
| `sample_budget` | `data/sample_budget.csv` |

Optional MCP server (same tools):

```bash
python3 -m tools.mcp_server
```

## Run the assistant

```bash
python3 -m interfaces.cli.assistant_cli
# or: python3 -m assistant.agent
```

Example prompts:

- “Reconcile sample_bank and sample_ledger. How many matched?”
- “Using sample actuals and budget, which accounts are flagged at 5%?”

The system prompt instructs the model to **never calculate financial numbers itself**, always call a tool, and always cite workflow name + version from lineage.

## Evals

Golden set: `evals/golden.json` (9 cases covering routing, reconciliation numbers, and variance numbers).

**Logic-only** (no API key — CI / offline smoke test):

```bash
python3 evals/run_evals.py --logic-only
```

**Full assistant eval** (needs `OPENAI_API_KEY`):

```bash
python3 evals/run_evals.py
```

Scoring:

1. Correct tool called  
2. Numerical fields within tolerance (default `0.01`)  
3. Lineage present on the tool result (and mentioned in the reply for assistant mode)

Results are written to `logs/eval_results.json`.

## Project layout

```
/
├── domain/workflows/          # pure business logic
├── application/               # use cases + ports
├── infrastructure/            # DB, cache, LLM, tools, config
├── interfaces/                # api, cli, mcp
├── migrations/ · data/
├── evals/ · tests/
├── docs/ARCHITECTURE.md
├── docs/CLEAN_ARCHITECTURE.md
├── logic/ · api/ · …          # compatibility shims
├── README.md
└── requirements.txt
```

## Tests

```bash
python3 -m unittest tests.test_edge_cases tests.test_api_and_cache -v
python3 evals/run_evals.py --logic-only
```

## Why this matters

In production finance teams, **numbers must come from versioned, testable logic** — not from an LLM’s next-token guess. This prototype shows the control plane in miniature:

1. Logic is pure, typed, and independently testable.  
2. The LLM is a conversational router + narrator.  
3. Lineage travels with every answer.  
4. Evals catch tool mis-routing and numeric drift.

### Performance notes (v1.0.2)

- Fast float money compares after quantized parse (no per-compare Decimal).
- CSV columns resolved once per file; headers normalized once.
- `include_details=false` on workflow APIs skips large row arrays.
- Result cache uses `deepcopy` instead of JSON round-trips; hit-rate in `/ready`.
- SQLite connections are thread-local + WAL; audit DB stores compact summaries.

### Production hardening notes (v1.0.1+)


- Optional tool numerics treat JSON `null` as the documented default (LLMs often send nulls).
- Invalid tool-argument JSON is caught and returned as an error payload (no process crash).
- CSV reads use `utf-8-sig` + header normalization (BOM / casing).
- Amounts accept accounting parentheses, e.g. `(1,250.00)`.
- Tolerances/thresholds must be `>= 0`; money compares use decimal quantization.
- Missing/empty sources return actionable errors that list known demo aliases.
