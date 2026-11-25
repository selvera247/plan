"""Compatibility shim — prefer ``infrastructure.cache``."""

from infrastructure.cache import ResultCache, cache_key, get_result_cache

__all__ = ["ResultCache", "cache_key", "get_result_cache"]
