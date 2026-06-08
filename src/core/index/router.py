"""Query router — dispatches to exact / prefix / fuzzy / contains indexes."""
from __future__ import annotations
from typing import List, Dict, Optional

from .exact import ExactIndex
from .trie import TrieIndex
from .bktree import BKTree
from ..cache.lru import LRUCache
from ...utils.logging import logger


class QueryRouter:
    """Routes queries to the fastest available index.

    Priority: cache -> exact -> prefix -> fuzzy(BKTree) -> contains
    Results are LRU-cached to avoid redundant work.
    """

    def __init__(self, exact: ExactIndex, trie: TrieIndex, cache: LRUCache,
                 bktree: Optional[BKTree] = None,
                 sorted_keys: list[str] | None = None,
                 raw_dict: dict[str, str] | None = None) -> None:
        self._exact = exact
        self._trie = trie
        self._bktree = bktree
        self._cache = cache
        self._sorted_keys = sorted_keys or []
        self._raw = raw_dict or {}

    def search(self, query: str, limit: int = 20) -> List[Dict[str, str]]:
        """Search with cascading fallback: cache -> exact -> prefix -> fuzzy -> contains."""
        if not query:
            return []

        q = query.strip().lower()
        if not q:
            return []

        # 1. Cache hit
        cached = self._cache.get(q)
        if cached is not None:
            return cached

        results: list[dict[str, str]] = []

        # 2. Exact match (always first)
        exact_def = self._exact.lookup(q)
        if exact_def is not None:
            results.append({"word": q, "definition": exact_def})

        # 3. Prefix match via Trie
        if len(results) < limit:
            prefix_results = self._trie.search_prefix(q, limit=limit)
            seen = {r["word"] for r in results}
            for r in prefix_results:
                if r["word"] not in seen:
                    results.append(r)
                    seen.add(r["word"])
                    if len(results) >= limit:
                        break

        # 4. Fuzzy match via BK-Tree (for typos / misspellings)
        if len(results) < 3 and self._bktree and self._bktree.size > 0:
            tolerance = 1 if len(q) <= 4 else 2
            fuzzy_results = self._bktree.search(q, tolerance=tolerance, limit=limit)
            seen = {r["word"] for r in results}
            for r in fuzzy_results:
                if r["word"] not in seen:
                    results.append(r)
                    seen.add(r["word"])
                    if len(results) >= limit:
                        break

        # 5. Contains fallback
        if len(results) < limit:
            seen = {r["word"] for r in results}
            for key in self._sorted_keys:
                if q in key and key not in seen and not key.startswith(q):
                    results.append({"word": key, "definition": self._raw[key]})
                    seen.add(key)
                    if len(results) >= limit:
                        break

        # Cache and return
        if results:
            self._cache.put(q, results)

        return results

    def stats(self) -> dict:
        return {
            "exact_size": self._exact.size,
            "trie_size": self._trie.size,
            "bktree_size": self._bktree.size if self._bktree else 0,
            "cache": self._cache.stats(),
        }
