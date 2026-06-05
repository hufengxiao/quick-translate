"""HashMap-based exact-match index — O(1) lookup."""
from __future__ import annotations
from typing import Optional

from ...utils.logging import logger


class ExactIndex:
    """Dict[str, str] wrapper with stats tracking."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self._loaded = False

    def load(self, entries: dict[str, str]) -> int:
        """Bulk-load entries. Returns count loaded."""
        self._data = entries
        self._loaded = True
        logger.debug("ExactIndex loaded {} entries", len(entries))
        return len(entries)

    def lookup(self, word: str) -> Optional[str]:
        """Exact match — O(1). Returns definition or None."""
        return self._data.get(word.lower())

    def has(self, word: str) -> bool:
        return word.lower() in self._data

    @property
    def size(self) -> int:
        return len(self._data)

    @property
    def is_loaded(self) -> bool:
        return self._loaded
