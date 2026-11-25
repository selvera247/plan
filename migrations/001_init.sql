-- Governed finance assistant — core audit + conversation schema
-- Compatible with SQLite and Postgres (use TEXT for UUIDs / JSON).

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    api_key_hash TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages(conversation_id, created_at);

CREATE TABLE IF NOT EXISTS workflow_runs (
    id TEXT PRIMARY KEY,
    workflow TEXT NOT NULL,
    version TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    inputs_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    lineage_json TEXT NOT NULL,
    cache_hit INTEGER NOT NULL DEFAULT 0,
    duration_ms REAL NOT NULL DEFAULT 0,
    conversation_id TEXT REFERENCES conversations(id),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_workflow_runs_hash
    ON workflow_runs(workflow, input_hash, created_at);

CREATE INDEX IF NOT EXISTS idx_workflow_runs_created
    ON workflow_runs(created_at);

CREATE TABLE IF NOT EXISTS tool_calls (
    id TEXT PRIMARY KEY,
    conversation_id TEXT REFERENCES conversations(id),
    message_id TEXT REFERENCES messages(id),
    run_id TEXT REFERENCES workflow_runs(id),
    tool_name TEXT NOT NULL,
    arguments_json TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tool_calls_conversation
    ON tool_calls(conversation_id, created_at);
