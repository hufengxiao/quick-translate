"""BK-Tree index for fuzzy/approximate search using Levenshtein distance.

BK-Tree allows finding all words within a given edit distance in
O(log n) average time, instead of O(n) brute force.
"""
from __future__ import annotations
from typing import List, Dict, Optional

from ...utils.logging import logger


def levenshtein(s: str, t: str) -> int:
    """Compute Levenshtein edit distance between two strings.
    Uses Wagner-Fischer algorithm with O(min(m,n)) space.
    """
    if s == t:
        return 0
    if not s:
        return len(t)
    if not t:
        return len(s)

    # Ensure s is the shorter string for space optimization
    if len(s) > len(t):
        s, t = t, s

    m, n = len(s), len(t)
    prev = list(range(m + 1))
    curr = [0] * (m + 1)

    for j in range(1, n + 1):
        curr[0] = j
        for i in range(1, m + 1):
            cost = 0 if s[i - 1] == t[j - 1] else 1
            curr[i] = min(
                prev[i] + 1,       # deletion
                curr[i - 1] + 1,   # insertion
                prev[i - 1] + cost, # substitution
            )
        prev, curr = curr, prev

    return prev[m]


class BKNode:
    __slots__ = ("word", "definition", "children")

    def __init__(self, word: str, definition: str) -> None:
        self.word = word
        self.definition = definition
        self.children: dict[int, BKNode] = {}


class BKTree:
    """BK-Tree for approximate string matching.

    Insert: O(log n) average
    Search: O(log n) average for small tolerance
    """

    def __init__(self) -> None:
        self._root: Optional[BKNode] = None
        self._size = 0

    def insert(self, word: str, definition: str) -> None:
        if not self._root:
            self._root = BKNode(word, definition)
            self._size = 1
            return

        node = self._root
        d = levenshtein(word, node.word)
        while d in node.children:
            node = node.children[d]
            d = levenshtein(word, node.word)

        node.children[d] = BKNode(word, definition)
        self._size += 1

    def search(self, query: str, tolerance: int = 2, limit: int = 20) -> List[Dict[str, str]]:
        """Find all words within `tolerance` edits of query."""
        if not self._root:
            return []

        results: list[dict[str, str]] = []
        stack = [self._root]

        while stack and len(results) < limit:
            node = stack.pop()
            d = levenshtein(query, node.word)
            if d <= tolerance:
                results.append({
                    "word": node.word,
                    "definition": node.definition,
                    "distance": d,
                })
            # Only explore children whose edge distance is in range [d-tolerance, d+tolerance]
            low = d - tolerance
            high = d + tolerance
            for dist, child in node.children.items():
                if low <= dist <= high:
                    stack.append(child)

        # Sort by edit distance (closer matches first)
        results.sort(key=lambda r: r["distance"])
        return results[:limit]

    def load(self, entries: dict[str, str]) -> int:
        """Bulk-load entries into the BK-Tree."""
        count = 0
        for word, defn in entries.items():
            self.insert(word, defn)
            count += 1
            # Yield GIL periodically so UI thread stays responsive
            if count % 2000 == 0:
                import time as _t
                _t.sleep(0.001)
        logger.debug("BKTree loaded {} entries", count)
        return count

    @property
    def size(self) -> int:
        return self._size
