# Governed Financial Assistant (Home-Lab Prototype)

A minimal, realistic prototype of a **governed finance assistant**: an OpenAI model answers finance questions by calling **deterministic Python workflows**, never by inventing numbers. Every tool response includes **lineage** (workflow name, version, inputs used) so answers are auditable.

This simulates a “data/logic → AI” pattern (similar in spirit to governed Alteryx/analytic workflows + an LLM front-end), implemented in pure Python.

## Architecture

```
User question
    ↓
OpenAI assistant (assistant/agent.py — Chat Completions + function calling)
    ↓  must call tools for any numeric / rule-based ask
Tool facade (tools/openai_tools.py)
    ├── registry (schemas, aliases, handlers)
    ├── audit log (logs/tool_calls.log)
    └── FastMCP exposure (tools/mcp_server.py)
    ↓
Deterministic logic (logic/reconcile.py, logic/variance.py)
    └── shared helpers (logic/common.py — lineage, parsing)
    ↓
Structured result + lineage
```

| Layer | Role |
|-------|------|
| `logic/` | Pure workflows + shared `common` helpers (lineage, parsing) |
| `tools/` | Registry, audit, OpenAI facade, optional FastMCP server |
| `assistant/` | System-prompted agent that refuses to do finance math itself |
| `evals/` | Golden questions (`tool_args` + expectations) + scoring module |
| `project_paths.py` | Repo root / data / log path constants |
| `data/` | Small realistic sample CSVs |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # then set OPENAI_API_KEY
```

Requires a single `OPENAI_API_KEY`. Optional: `OPENAI_MODEL` (default `gpt-4o-mini`).

## Workflows

### 1. Reconciliation — `logic/reconcile.py` v1.0.1

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

### 2. Variance analysis — `logic/variance.py` v1.0.1

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
python3 -m assistant.agent
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
├── project_paths.py
├── logic/
│   ├── common.py
│   ├── reconcile.py
│   ├── variance.py
│   └── __init__.py
├── tools/
│   ├── registry.py
│   ├── audit.py
│   ├── openai_tools.py
│   └── mcp_server.py
├── assistant/
│   └── agent.py
├── evals/
│   ├── golden.json
│   ├── scoring.py
│   └── run_evals.py
├── data/
│   ├── sample_transactions_bank.csv
│   ├── sample_transactions_ledger.csv
│   ├── sample_actuals.csv
│   └── sample_budget.csv
├── logs/                 # created at runtime
├── README.md
├── requirements.txt
└── .env.example
```

## Tests

```bash
python3 -m unittest tests.test_edge_cases -v
python3 evals/run_evals.py --logic-only
```

## Why this matters

In production finance teams, **numbers must come from versioned, testable logic** — not from an LLM’s next-token guess. This prototype shows the control plane in miniature:

1. Logic is pure, typed, and independently testable.  
2. The LLM is a conversational router + narrator.  
3. Lineage travels with every answer.  
4. Evals catch tool mis-routing and numeric drift.

### Production hardening notes (v1.0.1)

- Optional tool numerics treat JSON `null` as the documented default (LLMs often send nulls).
- Invalid tool-argument JSON is caught and returned as an error payload (no process crash).
- CSV reads use `utf-8-sig` + header normalization (BOM / casing).
- Amounts accept accounting parentheses, e.g. `(1,250.00)`.
- Tolerances/thresholds must be `>= 0`; money compares use decimal quantization.
- Missing/empty sources return actionable errors that list known demo aliases.
