# Governed Finance Assistant — System Architecture

## Product goal

A **governed** finance assistant: LLMs never invent numbers. Deterministic, versioned workflows compute results; the model routes questions and narrates lineage. Every answer is auditable.

## Target architecture (scalable)

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ Web / CLI   │   │ MCP clients │   │ Partner API │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       └────────────┬────┴────────────────┘
                    ▼
            API Gateway (FastAPI)
            • API-key auth
            • request IDs
            • rate limits
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   ChatService  WorkflowSvc  AuditService
        │           │           │
        ▼           ▼           │
   OpenAI API   logic/*  ◄──────┘ (lineage)
        │           │
        └─────┬─────┘
              ▼
     ┌────────────────┐
     │ Result Cache   │  (Redis in prod / LRU in MVP)
     │ key = workflow │
     │   + version    │
     │   + input hash │
     └────────┬───────┘
              ▼
     ┌────────────────┐
     │ Postgres       │  sessions, messages, workflow_runs, tool_calls
     └────────────────┘
```

### Component structure

| Component | Responsibility | Scale path |
|-----------|----------------|------------|
| `logic/` | Pure deterministic workflows | Stateless workers / queue later |
| `services/` | Application orchestration | Horizontal pods |
| `api/` | HTTP contract | Load-balanced FastAPI |
| `db/` | Persistence + migrations | Postgres primary + read replicas |
| `cache/` | Workflow result memoization | Redis cluster |
| `assistant/` | LLM tool-calling agent | Bounded concurrency |
| `tools/` | Tool registry / MCP | Sidecar or same process |

### Data flow

1. Client `POST /v1/chat` with question (+ optional `conversation_id`).
2. API authenticates, creates/loads conversation, appends user message.
3. ChatService invokes OpenAI with tool schemas; model selects a tool.
4. WorkflowService checks cache → on miss runs `logic/*`, stores run + lineage in DB, fills cache.
5. Tool result returns to the model; model narrates with workflow name/version.
6. Assistant message + tool_calls persisted; response returned with `run_ids` and lineage.

Direct numeric APIs (`POST /v1/workflows/reconcile`, `/variance`) skip the LLM for batch/automation.

### API design (v1)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness |
| `GET` | `/ready` | DB readiness |
| `POST` | `/v1/workflows/reconcile` | Deterministic recon |
| `POST` | `/v1/workflows/variance` | Deterministic variance |
| `POST` | `/v1/chat` | Multi-turn governed chat |
| `GET` | `/v1/conversations/{id}` | Conversation history |
| `GET` | `/v1/runs/{id}` | Workflow run + lineage |
| `GET` | `/v1/runs` | Recent runs (audit) |

Auth: `X-API-Key` header (MVP). Production: OIDC / service accounts.

### Database schema

```
conversations(id, created_at, updated_at, api_key_hash, metadata_json)
messages(id, conversation_id, role, content, created_at)
workflow_runs(
  id, workflow, version, input_hash, inputs_json, result_json,
  lineage_json, cache_hit, duration_ms, created_at, conversation_id NULL
)
tool_calls(
  id, conversation_id, message_id NULL, run_id NULL,
  tool_name, arguments_json, status, error, created_at
)
```

### Caching strategy

- **Key:** `sha256(workflow|version|canonical_json(inputs))`
- **Value:** workflow result (treat as immutable; no deepcopy/JSON copy on hit)
- **TTL:** configurable (default 15 min); invalidate on workflow version bump
- **MVP:** process-local LRU; **Prod:** Redis with the same key format
- Prefer `include_details=false` for large batch jobs (counts/totals only)
- Audit DB stores **compact** summaries (counts/totals/lineage), not full row arrays
- Never cache chat narrative text — only deterministic workflow outputs

### Performance notes

| Hot path | Strategy |
|----------|----------|
| Amount matching | Quantize on parse; float compare with epsilon (no Decimal per compare) |
| CSV ingest | Normalize headers once; resolve columns once per file |
| Large responses | `include_details=false` skips matched/item arrays |
| Cache hits | Immutable references (O(1)); hit rate exposed on `/ready` |
| SQLite | Thread-local connections, WAL, `synchronous=NORMAL` |

### Minimal production version (this repo)

Implements the architecture with:

- FastAPI HTTP API
- SQLite by default (Postgres via `DATABASE_URL`)
- In-memory LRU cache
- SQL schema in `migrations/`
- Services wrapping existing `logic/` + `assistant/`

Swap SQLite→Postgres and LRU→Redis without changing domain logic.
