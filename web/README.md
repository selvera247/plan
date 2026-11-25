# Governed Finance UI

Production-minded React + TypeScript console for the multi-agent finance API.

## Stack

- Vite 8 + React 19 + TypeScript
- Design tokens (`src/styles/tokens.css`) — Ledger Night
- Accessible primitives in `src/components/ui`
- Domain panels in `src/components/finance`

## Run

```bash
# API (repo root)
uvicorn interfaces.api.app:app --reload --port 8000

# UI
cd web && npm install && npm run dev
```

Vite proxies `/v1`, `/health`, and `/ready` to `http://127.0.0.1:8000`.

Optional: `VITE_API_KEY` if the API enforces `X-API-Key`.

## Component architecture

```
components/
  ui/           # reusable, a11y-first primitives
  finance/      # domain composition (trace, lineage, consoles)
lib/            # typed fetch client + shared types
styles/         # tokens + global atmosphere
```

### Props design principles

| Concern | Pattern |
| --- | --- |
| Labels | Required `label` on form controls; `hideLabel` uses visually-hidden text |
| Errors | `error` string → `aria-invalid` + `role="alert"` + `aria-describedby` |
| Loading | `loading` on Button disables + spinner; Skeleton/Spinner use `role="status"` |
| Dismiss | Alert `onDismiss` with explicit `aria-label` |
| Composition | Panel for interactive sections; EmptyState for zero-data |

## Usage examples

```tsx
import { Button, TextField, Alert, Panel } from "./components/ui";

<Panel title="Reconcile" description="Deterministic match">
  <TextField label="Left source" value={left} onChange={…} error={errs.left} required />
  <Button loading={busy} onClick={run}>Run</Button>
  {fail && <Alert tone="error" title="Failed" onDismiss={…}>{fail}</Alert>}
</Panel>
```

```tsx
import { Tabs, Skeleton } from "./components/ui";
import { AgentTrace, LineageMeta } from "./components/finance";

<Tabs
  label="Console views"
  items={[
    { id: "agents", label: "Agents", panel: <AskConsole /> },
    { id: "workflows", label: "Workflows", panel: <WorkflowPanel /> },
  ]}
/>
```

Keyboard: Tabs support Arrow / Home / End. Skip link jumps to `#main`. Focus moves to the live result region after an agent run.

## Build

```bash
cd web && npm run build
```
