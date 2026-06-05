"""Trie-based prefix index — O(m) prefix search, m = query length."""
from __future__ import annotations
from typing import List, Dict

from ...utils.logging import logger


class TrieNode:
    __slots__ = ("children", "definition", "is_word")

    def __init__(self) -> None:
        self.children: dict[str, TrieNode] = {}
        self.definition: str | None = None
        self.is_word: bool = False


class TrieIndex:
    """Trie tree for fast prefix matching."""

    def __init__(self) -> None:
        self._root = TrieNode()
        self._size = 0

    def insert(self, word: str, definition: str) -> None:
        """Insert a word with its definition."""
        node = self._root
        for ch in word:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        if not node.is_word:
            self._size += 1
        node.is_word = True
        node.definition = definition

    def load(self, entries: dict[str, str]) -> int:
        """Bulk-load entries into trie."""
        count = 0
        for word, defn in entries.items():
            self.insert(word, defn)
            count += 1
        logger.debug("TrieIndex loaded {} entries", count)
        return count

    def search_prefix(self, prefix: str, limit: int = 20) -> List[Dict[str, str]]:
        """Find all words starting with prefix. O(m + k) where k = results."""
        prefix_lower = prefix.lower()
        node = self._root
        for ch in prefix_lower:
            if ch not in node.children:
                return []
            node = node.children[ch]
        # DFS to collect results
        results: list[dict[str, str]] = []
        self._collect(node, prefix_lower, results, limit)
        return results

    def _collect(self, node: TrieNode, path: str, results: list, limit: int) -> None:
        if len(results) >= limit:
            return
        if node.is_word and node.definition is not None:
            results.append({"word": path, "definition": node.definition})
        for ch, child in sorted(node.children.items()):
            self._collect(child, path + ch, results, limit)

    @property
    def size(self) -> int:
        return self._size
