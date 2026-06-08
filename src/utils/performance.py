"""Performance monitoring — track query latency, cache hit rate, startup time."""
from __future__ import annotations
import time
from collections import deque
from dataclasses import dataclass, field

from .logging import logger


@dataclass
class PerfStats:
    """Aggregated performance statistics."""
    query_count: int = 0
    total_query_ms: float = 0.0
    min_query_ms: float = float("inf")
    max_query_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    startup_ms: float = 0.0
    dict_load_ms: float = 0.0
    dict_words: int = 0
    _recent_latencies: deque = field(default_factory=lambda: deque(maxlen=100))

    @property
    def avg_query_ms(self) -> float:
        return self.total_query_ms / self.query_count if self.query_count > 0 else 0.0

    @property
    def p95_query_ms(self) -> float:
        if not self._recent_latencies:
            return 0.0
        sorted_lat = sorted(self._recent_latencies)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    def record_query(self, latency_ms: float) -> None:
        self.query_count += 1
        self.total_query_ms += latency_ms
        self.min_query_ms = min(self.min_query_ms, latency_ms)
        self.max_query_ms = max(self.max_query_ms, latency_ms)
        self._recent_latencies.append(latency_ms)

    def report(self) -> str:
        return (
            f"Queries: {self.query_count} | "
            f"Avg: {self.avg_query_ms:.1f}ms | "
            f"P95: {self.p95_query_ms:.1f}ms | "
            f"Cache: {self.cache_hit_rate:.0%} | "
            f"Dict: {self.dict_words} words | "
            f"Startup: {self.startup_ms:.0f}ms"
        )


# Global singleton
_stats = PerfStats()


def get_stats() -> PerfStats:
    return _stats


def timed(fn):
    """Decorator to time a function call and record to stats."""
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = (time.perf_counter() - t0) * 1000
        _stats.record_query(elapsed)
        return result
    return wrapper


def log_slow(threshold_ms: float = 50):
    """Decorator to log slow operations."""
    def decorator(fn):
        def wrapper(*args, **kwargs):
            t0 = time.perf_counter()
            result = fn(*args, **kwargs)
            elapsed = (time.perf_counter() - t0) * 1000
            if elapsed > threshold_ms:
                logger.warning("Slow {}: {:.1f}ms (threshold={:.0f}ms)",
                               fn.__name__, elapsed, threshold_ms)
            return result
        return wrapper
    return decorator
