"""SQLite (default) or Postgres via DATABASE_URL — one access path."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol

from project_paths import ROOT

DEFAULT_SQLITE = ROOT / "data" / "governed_finance.db"
MIGRATIONS_DIR = ROOT / "migrations"


class DbConnection(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> Any: ...
    def executemany(self, sql: str, seq: Any) -> Any: ...
    def commit(self) -> None: ...
    def close(self) -> None: ...
    @property
    def row_factory(self) -> Any: ...


def _database_url() -> str:
    return (os.getenv("DATABASE_URL") or "").strip()


def _sqlite_path() -> Path:
    raw = os.getenv("SQLITE_PATH", str(DEFAULT_SQLITE))
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect_sqlite() -> sqlite3.Connection:
    conn = sqlite3.connect(_sqlite_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _connect_postgres():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "DATABASE_URL is set but psycopg is not installed. "
            "pip install 'psycopg[binary]'"
        ) from exc

    conn = psycopg.connect(_database_url(), row_factory=dict_row)
    return conn


def connect() -> Any:
    if _database_url().startswith(("postgres://", "postgresql://")):
        return _connect_postgres()
    return _connect_sqlite()


@contextmanager
def get_connection() -> Iterator[Any]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _adapt_sql(sql: str) -> str:
    """Migrations use `?` placeholders conceptually; Postgres needs `%s` at runtime.
    Schema DDL is written to work on both engines.
    """
    if _database_url().startswith(("postgres://", "postgresql://")):
        return sql  # DDL only in migrations; runtime SQL adapted in repository
    return sql


def init_db() -> None:
    """Apply SQL migrations in order (idempotent CREATE IF NOT EXISTS)."""
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    with get_connection() as conn:
        for path in files:
            sql = path.read_text(encoding="utf-8")
            if hasattr(conn, "executescript"):
                conn.executescript(sql)
            else:
                # psycopg: run statements split on semicolons carefully enough for our DDL
                for statement in sql.split(";"):
                    stmt = statement.strip()
                    if stmt:
                        conn.execute(stmt)
