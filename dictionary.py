"""本地词典查询模块 — MDX 原生词典 + JSON fallback"""
import json
import os
import re
from typing import List, Dict, Optional


class Dictionary:
    """本地词典，支持 MDX 原生词典和 JSON fallback"""

    def __init__(self, dict_path: str, mdx_dict=None):
        self.entries: Dict[str, str] = {}
        self.sorted_keys: List[str] = []
        self.dict_path = dict_path
        self._mdx = mdx_dict  # MDXDictionary instance (optional)
        self._load()

    def _load(self):
        if not os.path.exists(self.dict_path):
            print(f"[Dict] Dictionary file not found: {self.dict_path}")
            return
        try:
            with open(self.dict_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self.entries = data
            elif isinstance(data, list):
                self.entries = {item["word"]: item["definition"] for item in data if "word" in item}
            self.sorted_keys = sorted(self.entries.keys())
            print(f"[Dict] JSON fallback: {len(self.entries)} entries")
        except Exception as e:
            print(f"[Dict] Failed to load JSON: {e}")

        if self._mdx and self._mdx.is_ready:
            print(f"[Dict] MDX primary: {self._mdx.word_count:,} entries")

    def search_prefix(self, prefix: str, limit: int = 20) -> List[Dict[str, str]]:
        if not prefix:
            return []
        # MDX first
        if self._mdx and self._mdx.is_ready:
            results = self._mdx.search_prefix(prefix, limit)
            if results:
                return results
        # JSON fallback
        prefix_lower = prefix.lower()
        results = []
        for key in self.sorted_keys:
            if key.startswith(prefix_lower):
                results.append({"word": key, "definition": self.entries[key]})
                if len(results) >= limit:
                    break
        return results

    def search_fuzzy(self, query: str, limit: int = 20) -> List[Dict[str, str]]:
        if not query:
            return []
        query_lower = query.lower()
        results = []

        # MDX exact match first
        if self._mdx and self._mdx.is_ready:
            entry = self._mdx.lookup(query_lower)
            if entry:
                results.append({
                    "word": entry["word"],
                    "definition": entry["definition"],
                    "text": entry.get("text", ""),
                })

        # MDX prefix match
        if self._mdx and self._mdx.is_ready:
            mdx_results = self._mdx.search_prefix(query_lower, limit)
            seen = {r["word"] for r in results}
            for r in mdx_results:
                if r["word"] not in seen:
                    results.append(r)
                    seen.add(r["word"])
                    if len(results) >= limit:
                        break

        # JSON fallback if no MDX results
        if not results:
            if query_lower in self.entries:
                results.append({"word": query_lower, "definition": self.entries[query_lower]})
            for key in self.sorted_keys:
                if key.startswith(query_lower) and key != query_lower:
                    results.append({"word": key, "definition": self.entries[key]})
                    if len(results) >= limit:
                        break
            if len(results) < limit:
                for key in self.sorted_keys:
                    if query_lower in key and not key.startswith(query_lower):
                        results.append({"word": key, "definition": self.entries[key]})
                        if len(results) >= limit:
                            break

        return results

    def lookup(self, word: str) -> Optional[str]:
        """精确查找 — MDX first, JSON fallback"""
        if self._mdx and self._mdx.is_ready:
            entry = self._mdx.lookup(word.lower())
            if entry:
                return entry.get("text") or entry.get("definition", "")
        return self.entries.get(word.lower())

    def lookup_rich(self, word: str) -> Optional[Dict[str, str]]:
        """精确查找 — 返回完整信息（含 HTML）"""
        if self._mdx and self._mdx.is_ready:
            return self._mdx.lookup(word.lower())
        defn = self.entries.get(word.lower())
        if defn:
            return {"word": word.lower(), "definition": defn, "text": defn}
        return None

    @property
    def word_count(self) -> int:
        if self._mdx and self._mdx.is_ready:
            return self._mdx.word_count
        return len(self.entries)
