"""本地词典查询模块"""
import json
import os
import re
from typing import List, Dict, Optional


class Dictionary:
    """本地词典，支持前缀匹配和精确查找"""

    def __init__(self, dict_path: str):
        self.entries: Dict[str, str] = {}
        self.sorted_keys: List[str] = []
        self.dict_path = dict_path
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
            print(f"[Dict] Loaded {len(self.entries)} entries")
        except Exception as e:
            print(f"[Dict] Failed to load: {e}")

    def search_prefix(self, prefix: str, limit: int = 20) -> List[Dict[str, str]]:
        """前缀匹配搜索"""
        if not prefix:
            return []
        prefix_lower = prefix.lower()
        results = []
        for key in self.sorted_keys:
            if key.startswith(prefix_lower):
                results.append({"word": key, "definition": self.entries[key]})
                if len(results) >= limit:
                    break
        return results

    def search_fuzzy(self, query: str, limit: int = 20) -> List[Dict[str, str]]:
        """模糊匹配搜索（包含）"""
        if not query:
            return []
        query_lower = query.lower()
        results = []
        # exact match first
        if query_lower in self.entries:
            results.append({"word": query_lower, "definition": self.entries[query_lower]})
        # prefix match
        for key in self.sorted_keys:
            if key.startswith(query_lower) and key != query_lower:
                results.append({"word": key, "definition": self.entries[key]})
                if len(results) >= limit:
                    break
        # contains match if not enough results
        if len(results) < limit:
            for key in self.sorted_keys:
                if query_lower in key and not key.startswith(query_lower):
                    results.append({"word": key, "definition": self.entries[key]})
                    if len(results) >= limit:
                        break
        return results

    def lookup(self, word: str) -> Optional[str]:
        """精确查找单词释义"""
        return self.entries.get(word.lower())

    @property
    def word_count(self) -> int:
        return len(self.entries)
