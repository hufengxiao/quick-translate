"""Dictionary facade — orchestrates lazy loading, indexing, caching, and routing."""
from __future__ import annotations
import os
import time
from typing import List, Dict, Optional, Callable

from ..index.exact import ExactIndex
from ..index.trie import TrieIndex
from ..index.router import QueryRouter
from ..cache.lru import LRUCache
from ..lazy.loader import LazyDictLoader
from ...utils.logging import logger


class Dictionary:
    """High-performance dictionary with cascading index strategy.
    
    Architecture:
        LazyDictLoader (2-phase load)
            → ExactIndex (HashMap O(1))
            → TrieIndex (Trie O(m) prefix)
            → LRUCache (result cache)
            → QueryRouter (unified dispatch)
    """

    def __init__(self, dict_path: str, preload_count: int = 10000,
                 cache_size: int = 500) -> None:
        self._dict_path = dict_path
        self._exact = ExactIndex()
        self._trie = TrieIndex()
        self._cache = LRUCache(max_size=cache_size)
        self._loader = LazyDictLoader(dict_path, preload_count)
        self._router: Optional[QueryRouter] = None
        self._ready = False
        self._load_start = 0.0

    def load(self, on_background_complete: Optional[Callable] = None) -> None:
        """Load dictionary with 2-phase strategy.
        
        Phase 1 (sync): Load top-N words → index them → ready to search
        Phase 2 (async): Load remaining words in background
        """
        self._load_start = time.perf_counter()

        def on_phase2_done(data: dict, keys: list[str]):
            self._build_indexes(data, keys)
            elapsed = (time.perf_counter() - self._load_start) * 1000
            logger.info("Dictionary fully loaded: {} words in {:.0f}ms", len(data), elapsed)
            if on_background_complete:
                on_background_complete()

        try:
            data = self._loader.load_preload_then_background(on_phase2_done)
        except Exception as e:
            logger.error("Dictionary load failed: {}", e)
            data = {}

        # Build indexes for preload data
        self._build_indexes(data, self._loader.sorted_keys)
        self._ready = True

        elapsed = (time.perf_counter() - self._load_start) * 1000
        logger.info("Dictionary ready (preload): {} words in {:.0f}ms",
                     len(data), elapsed)

    def _build_indexes(self, data: dict[str, str], sorted_keys: list[str]) -> None:
        """Build all indexes from data.

        Creates NEW index objects and atomically swaps references so the main
        thread never sees a half-built trie.
        """
        new_exact = ExactIndex()
        new_exact.load(data)
        new_trie = TrieIndex()
        new_trie.load(data)
        # Atomic swap — main thread sees complete indexes only
        self._exact = new_exact
        self._trie = new_trie
        self._router = QueryRouter(
            exact=self._exact,
            trie=self._trie,
            cache=self._cache,
            sorted_keys=sorted_keys,
            raw_dict=data,
        )

    def search(self, query: str, limit: int = 20) -> List[Dict[str, str]]:
        """Search with cascading fallback. Results are cached."""
        if not self._ready or not self._router:
            return []
        return self._router.search(query, limit)

    def lookup(self, word: str) -> Optional[str]:
        """Exact lookup — O(1)."""
        return self._exact.lookup(word.lower())

    @property
    def word_count(self) -> int:
        return self._exact.size

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def is_fully_loaded(self) -> bool:
        return self._loader.is_fully_loaded

    @property
    def cache_stats(self) -> dict:
        return self._cache.stats() if self._cache else {}
