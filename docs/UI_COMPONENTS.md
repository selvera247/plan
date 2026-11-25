# UI component library

Ledger Night console for the governed finance API. Built for loading states, empty/error edges, responsive layout, and accessibility.

## Architecture

```
web/src/
  styles/tokens.css      # color, type, space, focus ring
  styles/global.css      # atmosphere + layout utilities
  components/ui/         # reusable primitives
  components/finance/    # domain composition
  lib/api.ts             # typed fetch + abort + error parse
  lib/types.ts           # AgentRun / Workflow / Lineage
```

**Primitives** stay presentation-only. **Finance** components own fetch lifecycle, validation, and lineage display.

## Props design

| Prop | Purpose |
|------|---------|
| `label` (required on fields) | Always associates a visible or visually-hidden label |
| `hint` / `error` | Wired via `aria-describedby`; errors use `role="alert"` |
| `loading` (Button) | Sets `aria-busy`, disables, swaps icon for Spinner |
| `tone` (Alert/Badge) | Maps to semantic colors + live region aggressiveness |
| `onDismiss` (Alert) | Optional close with accessible name |
| Tabs `label` | Names the `tablist` for screen readers |

## Accessibility checklist

- Skip link → `#main`
- `:focus-visible` mint ring on interactive controls
- Keyboard tabs (←/→/Home/End)
- Live regions for agent results and alerts
- Form validation without relying on color alone
- Cancel/abort in-flight fetches

## Usage

### Button

```tsx
<Button variant="primary" loading={busy} onClick={save}>
  Save
</Button>
<Button variant="secondary" size="sm">Cancel</Button>
<Button variant="danger" disabled={!canDelete}>Delete</Button>
```

### TextField / TextArea / SelectField

```tsx
<TextField
  label="Left source"
  value={left}
  onChange={(e) => setLeft(e.target.value)}
  hint="Alias or path"
  error={errors.left}
  required
/>
```

### Alert + EmptyState + Skeleton

```tsx
{loading && <Skeleton height="4rem" label="Loading run" />}
{!loading && !data && <EmptyState title="No run yet" description="Submit to begin." />}
{err && (
  <Alert tone="error" title="Request failed" onDismiss={() => setErr(null)}>
    {err}
  </Alert>
)}
```

### Domain: AgentTrace + LineageMeta

```tsx
<LineageMeta lineage={res.lineage} runId={res.run_id} cacheHit={res.cache_hit} />
<AgentTrace steps={res.trace} loading={busy} />
```

Screens: `AskConsole` → `POST /v1/agents/run`; `WorkflowPanel` → reconcile/variance.
