# Clean Architecture

Behavior is unchanged; structure follows dependency rule: **inner layers never import outer layers**.

```
                 ┌──────────────────────────┐
                 │   interfaces/            │  HTTP · CLI · MCP
                 │   (controllers)          │
                 └────────────┬─────────────┘
                              │ depends on
                 ┌────────────▼─────────────┐
                 │   application/           │  use cases · ports
                 │   WorkflowService        │
                 │   GovernedChatService    │
                 └────────────┬─────────────┘
                              │ depends on
                 ┌────────────▼─────────────┐
                 │   domain/                │  pure workflows
                 │   workflows/*            │  (no frameworks)
                 └──────────────────────────┘
                              ▲
                 ┌────────────┴─────────────┐
                 │   infrastructure/        │  adapters
                 │   persistence · cache    │  implement ports
                 │   llm · tools · config   │
                 └──────────────────────────┘
```

## Folder structure

```
domain/                 # Enterprise business rules
  workflows/
    common.py
    reconcile.py
    variance.py

application/            # Application business rules
  ports.py              # Protocols (ResultCachePort, AuditRepositoryPort, …)
  workflow_service.py
  chat_service.py

infrastructure/         # Frameworks & drivers
  config/paths.py
  persistence/          # SQLite/Postgres
  cache/                # LRU result cache
  llm/                  # OpenAI assistant
  tools/                # Tool registry + audit log

interfaces/             # Delivery mechanisms
  api/                  # FastAPI
  cli/                  # Interactive assistant CLI
  mcp/                  # FastMCP server

# Compatibility shims (old import paths still work):
logic/  services/  tools/  api/  db/  cache/  assistant/  project_paths.py
```

## Dependency rules

| Layer | May import |
|-------|------------|
| `domain` | stdlib only |
| `application` | `domain`, `application.ports`, and **adapters via composition** (currently concrete infra for the minimal prod slice) |
| `infrastructure` | `domain`, stdlib, third-party |
| `interfaces` | `application`, `infrastructure` (wiring), schemas |

Ideal future step: inject all infra through `ports.py` constructors only (no direct infra imports inside application). Ports are already defined; WorkflowService accepts `ResultCachePort`.

## Entry points

| Concern | Command |
|---------|---------|
| API | `uvicorn interfaces.api.app:app --port 8000` (or `api.app:app`) |
| CLI | `python3 -m interfaces.cli.assistant_cli` (or `python3 -m assistant.agent`) |
| MCP | `python3 -m interfaces.mcp.server` |
| Evals | `python3 evals/run_evals.py --logic-only` |

## Why this split

- **domain** stays testable without DB/LLM.
- **application** owns orchestration (cache + audit + workflow calls).
- **infrastructure** can swap SQLite→Postgres or LRU→Redis behind the same ports.
- **interfaces** stay thin: validate input, call a use case, return DTO.
