import { AskConsole } from "./components/finance/AskConsole";
import { WorkflowPanel } from "./components/finance/WorkflowPanel";
import { ApiStatus } from "./components/finance/ApiStatus";
import { Tabs } from "./components/ui";

export default function App() {
  return (
    <>
      <a className="gf-skip-link" href="#main">
        Skip to content
      </a>
      <div className="gf-app">
        <header style={{ marginBottom: "2rem" }}>
          <div className="gf-row" style={{ justifyContent: "space-between" }}>
            <p
              style={{
                margin: 0,
                fontSize: "0.75rem",
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: "var(--gf-accent)",
                fontWeight: 600,
              }}
            >
              Governed Finance
            </p>
            <ApiStatus />
          </div>
          <h1 className="gf-brand">Ledger Night</h1>
          <p className="gf-lede">
            Ask in natural language or run deterministic reconcile and variance
            workflows. Every answer carries lineage — the LLM never invents
            numbers.
          </p>
        </header>

        <main id="main">
          <Tabs
            label="Console views"
            items={[
              {
                id: "agents",
                label: "Agents",
                panel: <AskConsole />,
              },
              {
                id: "workflows",
                label: "Workflows",
                panel: <WorkflowPanel />,
              },
            ]}
          />
        </main>

        <footer
          style={{
            marginTop: "3rem",
            color: "var(--gf-muted)",
            fontSize: "0.8rem",
          }}
        >
          <p style={{ margin: 0 }}>
            UI kit: accessible Button, fields, Alert, Skeleton, Tabs, Panel.
            Proxy → <code className="gf-mono">/v1</code> on :8000.
          </p>
        </footer>
      </div>
    </>
  );
}
