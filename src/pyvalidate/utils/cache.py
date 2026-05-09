"""
pyvalidate.utils.cache
~~~~~~~~~~~~~~~~~~~~~~~~
LRU cache for validator results, keyed by (validator_class_name, value_repr).
"""
from __future__ import annotations

import functools
import threading
from collections import OrderedDict
from typing import Any, Optional, Tuple

from pyvalidate.base import ValidationResult

CacheKey = Tuple[str, str]


class ValidationCache:
    """Thread-safe LRU cache for :class:`ValidationResult` objects.

    Keyed by a ``(validator_class_name, repr(value))`` tuple.
    Use with stateless validators only (those with no side effects).

    Parameters
    ----------
    max_size:
        Maximum number of entries before eviction. Default 512.
    """

    def __init__(self, max_size: int = 512) -> None:
        self._max_size = max_size
        self._store: OrderedDict[CacheKey, ValidationResult] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, validator_class: str, value: Any) -> CacheKey:
        try:
            value_repr = repr(value)
        except Exception:
            value_repr = f"<unrepr:{id(value)}>"
        return (validator_class, value_repr)

    def get(self, validator_class: str, value: Any) -> Optional[ValidationResult]:
        """Return cached result or None if not found."""
        key = self._make_key(validator_class, value)
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                self._hits += 1
                return self._store[key]
            self._misses += 1
            return None

    def set(self, validator_class: str, value: Any, result: ValidationResult) -> None:
        """Store *result* in the cache, evicting LRU entry if at capacity."""
        key = self._make_key(validator_class, value)
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            else:
                if len(self._store) >= self._max_size:
                    self._store.popitem(last=False)
                self._store[key] = result

    def invalidate(self, validator_class: Optional[str] = None) -> int:
        """Remove cache entries.

        If *validator_class* is given, remove only entries for that class.
        Otherwise clear everything. Returns number of entries removed.
        """
        with self._lock:
            if validator_class is None:
                count = len(self._store)
                self._store.clear()
                return count
            keys_to_remove = [k for k in self._store if k[0] == validator_class]
            for k in keys_to_remove:
                del self._store[k]
            return len(keys_to_remove)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)

    def stats(self) -> dict:
        return {
            "size": self.size,
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 4),
        }

    def __repr__(self) -> str:
        return (
            f"ValidationCache(size={self.size}/{self._max_size}, "
            f"hit_rate={self.hit_rate:.1%})"
        )


# Module-level default cache instance
_default_cache: ValidationCache = ValidationCache(max_size=512)


def get_default_cache() -> ValidationCache:
    return _default_cache


def cached_validate(validator_instance: Any, value: Any) -> Optional[ValidationResult]:
    """Look up a cached result for the given validator + value pair."""
    cls_name = type(validator_instance).__name__
    return _default_cache.get(cls_name, value)


def cache_result(validator_instance: Any, value: Any, result: ValidationResult) -> None:
    """Store a validation result in the default cache."""
    cls_name = type(validator_instance).__name__
    _default_cache.set(cls_name, value, result)
