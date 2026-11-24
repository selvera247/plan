"""Single source of truth for repo paths and import bootstrap."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
ENV_FILE = ROOT / ".env"


def ensure_repo_on_path() -> Path:
    """Make the repo root importable when running modules as scripts."""
    root = str(ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    return ROOT
