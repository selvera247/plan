"""
Workflow result cache.

MVP: process-local LRU with TTL.
Prod swap: same interface backed by Redis (identical key format).
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import OrderedDict
from typing import Any


def cache_key(workflow: str, version: str, inputs: dict[str, Any]) -> str:
    canonical = json.dumps(inputs, sort_keys=True, default=str, separators=(",", ":"))
    digest = hashlib.sha256(
        f"{workflow}|{version}|{canonical}".encode("utf-8")
    ).hexdigest()
    return f"wf:{workflow}:v{version}:{digest}"


class ResultCache:
    def __init__(self, *, max_entries: int = 256, ttl_seconds: float = 900.0) -> None:
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._data: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, value = item
            if time.time() > expires_at:
                del self._data[key]
                return None
            self._data.move_to_end(key)
            return json.loads(json.dumps(value))  # defensive copy

    def set(self, key: str, value: dict[str, Any]) -> None:
        with self._lock:
            self._data[key] = (time.time() + self.ttl_seconds, value)
            self._data.move_to_end(key)
            while len(self._data) > self.max_entries:
                self._data.popitem(last=False)

    def invalidate_prefix(self, prefix: str) -> int:
        with self._lock:
            keys = [k for k in self._data if k.startswith(prefix)]
            for k in keys:
                del self._data[k]
            return len(keys)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "backend": "memory_lru",
                "entries": len(self._data),
                "max_entries": self.max_entries,
                "ttl_seconds": self.ttl_seconds,
            }


_CACHE: ResultCache | None = None


def get_result_cache() -> ResultCache:
    global _CACHE
    if _CACHE is None:
        _CACHE = ResultCache(
            max_entries=int(os.getenv("CACHE_MAX_ENTRIES", "256")),
            ttl_seconds=float(os.getenv("CACHE_TTL_SECONDS", "900")),
        )
    return _CACHE
