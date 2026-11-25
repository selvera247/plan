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
    """
    Thread-safe LRU+TTL cache.

    Cached payloads are treated as **immutable**. We avoid JSON/deepcopy on the
    hot path so large workflow results stay cheap to serve. Callers must not
    mutate returned dicts (API serialization is read-only).
    """

    def __init__(self, *, max_entries: int = 256, ttl_seconds: float = 900.0) -> None:
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._data: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                self.misses += 1
                return None
            expires_at, value = item
            if time.monotonic() > expires_at:
                del self._data[key]
                self.misses += 1
                return None
            self._data.move_to_end(key)
            self.hits += 1
            return value

    def set(self, key: str, value: dict[str, Any]) -> None:
        with self._lock:
            self._data[key] = (time.monotonic() + self.ttl_seconds, value)
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
            total = self.hits + self.misses
            return {
                "backend": "memory_lru",
                "entries": len(self._data),
                "max_entries": self.max_entries,
                "ttl_seconds": self.ttl_seconds,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": round(self.hits / total, 4) if total else 0.0,
            }


_CACHE: ResultCache | None = None
_CACHE_LOCK = threading.Lock()


def get_result_cache() -> ResultCache:
    global _CACHE
    if _CACHE is None:
        with _CACHE_LOCK:
            if _CACHE is None:
                _CACHE = ResultCache(
                    max_entries=int(os.getenv("CACHE_MAX_ENTRIES", "256")),
                    ttl_seconds=float(os.getenv("CACHE_TTL_SECONDS", "900")),
                )
    return _CACHE
