"""Pinyin index — search Chinese words/characters by pinyin input.

Builds a reverse index: pinyin string → list of Chinese words found
in dictionary definitions. Uses pypinyin for romanisation.
Caches to disk as pickle for fast subsequent loads.

Example: typing "nihao" finds "你好".
"""
from __future__ import annotations
import os
import pickle
import re
import time
from typing import List, Dict, Optional

from ...utils.logging import logger

try:
    from pypinyin import pinyin as _pinyin, Style
    _HAS_PYPINYIN = True
except ImportError:
    _HAS_PYPINYIN = False


def _chinese_to_pinyin_key(text: str) -> str:
    """Convert Chinese text to a concatenated pinyin key (no tones, lowercase)."""
    if not _HAS_PYPINYIN:
        return ""
    syllables = _pinyin(text, style=Style.NORMAL)
    return "".join(s[0] for s in syllables).lower()


# Regex: 2-8 consecutive CJK Unified Ideographs
_CJK_RE = re.compile(r"[\u4e00-\u9fff]{2,8}")


class PinyinIndex:
    """Maps pinyin strings to Chinese words extracted from dictionary definitions.

    Built at dictionary-load time by scanning all definition values for
    Chinese character sequences and converting them to pinyin keys.
    Uses pickle disk cache keyed on dict file mtime for fast reloads.
    """

    def __init__(self, cache_path: Optional[str] = None) -> None:
        self._index: Dict[str, List[Dict[str, str]]] = {}
        self._size = 0
        self._cache_path = cache_path

    def build_from_entries(self, entries: Dict[str, str],
                           dict_mtime: float = 0.0) -> int:
        """Scan dictionary definitions and build pinyin → Chinese-word index.

        Args:
            entries: {english_word: chinese_definition} mapping.
            dict_mtime: modification time of the source dict file (for cache).

        Returns:
            Number of pinyin→word mappings created.
        """
        if not _HAS_PYPINYIN:
            logger.warning("pypinyin not installed — pinyin index disabled")
            return 0

        # Try disk cache first
        if self._cache_path and os.path.exists(self._cache_path):
            try:
                with open(self._cache_path, "rb") as f:
                    cache_mtime, index = pickle.load(f)
                if cache_mtime >= dict_mtime:
                    self._index = index
                    self._size = sum(len(v) for v in index.values())
                    logger.debug("PinyinIndex loaded from cache: {} keys", len(index))
                    return self._size
            except Exception:
                pass  # cache invalid, rebuild

        t0 = time.perf_counter()
        index: Dict[str, List[Dict[str, str]]] = {}
        count = 0

        for eng_word, definition in entries.items():
            for cjk in _CJK_RE.findall(definition):
                py = _chinese_to_pinyin_key(cjk)
                if not py:
                    continue
                bucket = index.get(py)
                if bucket is None:
                    bucket = []
                    index[py] = bucket
                # Dedup within bucket
                if not any(r["word"] == cjk for r in bucket):
                    bucket.append({
                        "word": cjk,
                        "definition": definition[:300],
                        "source": eng_word,
                    })
                    count += 1

        self._index = index
        self._size = count
        elapsed = time.perf_counter() - t0
        logger.debug("PinyinIndex built {} mappings ({} keys) in {:.1f}s",
                      count, len(index), elapsed)

        # Save to disk cache
        if self._cache_path:
            try:
                with open(self._cache_path, "wb") as f:
                    pickle.dump((dict_mtime, index), f)
                logger.debug("PinyinIndex cache saved to {}", self._cache_path)
            except Exception:
                pass

        return count

    def search(self, query: str, limit: int = 20) -> List[Dict[str, str]]:
        """Look up a pinyin query string.

        Only matches when the query looks like pinyin (all ASCII letters).
        Returns list of {word, definition} dicts.
        """
        if not query or not _HAS_PYPINYIN:
            return []

        q = query.strip().lower()
        if not q or not q.isalpha():
            return []

        bucket = self._index.get(q)
        if not bucket:
            return []

        # Return top results, formatted like other index results
        return [
            {"word": r["word"], "definition": r["definition"]}
            for r in bucket[:limit]
        ]

    def lookup_chinese(self, chinese_text: str) -> Optional[str]:
        """Get pinyin for a Chinese word (utility)."""
        if not _HAS_PYPINYIN or not chinese_text:
            return None
        return _chinese_to_pinyin_key(chinese_text)

    @property
    def size(self) -> int:
        """Number of pinyin→word mappings."""
        return self._size

    @property
    def key_count(self) -> int:
        """Number of unique pinyin keys."""
        return len(self._index)
