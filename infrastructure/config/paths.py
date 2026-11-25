"""Single source of truth for repo paths and import bootstrap."""

from __future__ import annotations

import sys
from pathlib import Path

# infrastructure/config/paths.py → repo root is two levels up
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
ENV_FILE = ROOT / ".env"
MIGRATIONS_DIR = ROOT / "migrations"


def ensure_repo_on_path() -> Path:
    """Make the repo root importable when running modules as scripts."""
    root = str(ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    return ROOT
