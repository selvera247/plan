"""SQLite (default) or Postgres via DATABASE_URL — pooled for performance."""

from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol

from project_paths import ROOT

DEFAULT_SQLITE = ROOT / "data" / "governed_finance.db"
MIGRATIONS_DIR = ROOT / "migrations"

_sqlite_local = threading.local()
_sqlite_write_lock = threading.Lock()


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
    conn = sqlite3.connect(_sqlite_path(), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn


def _thread_sqlite() -> sqlite3.Connection:
    """Reuse one SQLite connection per thread (avoids connect/close per request)."""
    conn = getattr(_sqlite_local, "conn", None)
    if conn is None:
        conn = _connect_sqlite()
        _sqlite_local.conn = conn
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

    return psycopg.connect(_database_url(), row_factory=dict_row)


def connect() -> Any:
    if _database_url().startswith(("postgres://", "postgresql://")):
        return _connect_postgres()
    return _thread_sqlite()


def _is_postgres() -> bool:
    return _database_url().startswith(("postgres://", "postgresql://"))


@contextmanager
def get_connection() -> Iterator[Any]:
    """
    Yield a DB connection.

    SQLite: thread-local reuse + write lock (no per-call open/close).
    Postgres: short-lived connection (swap for a real pool in larger deploys).
    """
    if _is_postgres():
        conn = _connect_postgres()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return

    conn = _thread_sqlite()
    with _sqlite_write_lock:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def reset_sqlite_pool() -> None:
    """Close thread-local SQLite connection (used by tests when SQLITE_PATH changes)."""
    conn = getattr(_sqlite_local, "conn", None)
    if conn is not None:
        try:
            conn.close()
        finally:
            _sqlite_local.conn = None


def init_db() -> None:
    """Apply SQL migrations in order (idempotent CREATE IF NOT EXISTS)."""
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    with get_connection() as conn:
        for path in files:
            sql = path.read_text(encoding="utf-8")
            if hasattr(conn, "executescript"):
                conn.executescript(sql)
            else:
                for statement in sql.split(";"):
                    stmt = statement.strip()
                    if stmt:
                        conn.execute(stmt)
