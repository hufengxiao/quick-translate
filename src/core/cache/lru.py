"""LRU query result cache — avoids redundant lookups."""
from __future__ import annotations
from collections import OrderedDict
from typing import Optional, List, Dict
import threading
import time

from ...utils.logging import logger


class LRUCache:
    """Thread-safe LRU cache for query results."""

    def __init__(self, max_size: int = 500) -> None:
        self._cache: OrderedDict[str, tuple[list[dict[str, str]], float]] = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
        self._lock = threading.Lock()

    def get(self, query: str) -> Optional[List[Dict[str, str]]]:
        """Get cached results. Returns None on miss."""
        key = query.lower().strip()
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._hits += 1
                results, _ = self._cache[key]
                return results
            self._misses += 1
        return None

    def put(self, query: str, results: List[Dict[str, str]]) -> None:
        """Cache query results."""
        key = query.lower().strip()
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (results, time.time())
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def invalidate(self, query: str) -> None:
        key = query.lower().strip()
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def size(self) -> int:
        return len(self._cache)

    def stats(self) -> dict:
        return {
            "size": self.size,
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self.hit_rate:.1%}",
        }
