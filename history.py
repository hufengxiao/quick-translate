"""查词历史管理 - 本地保存最近 50 条查询"""
import json
import os
from datetime import datetime


class SearchHistory:
    """查词历史，保存到 ~/.quick-translate/history.json"""

    def __init__(self, max_size=50):
        self.max_size = max_size
        self.entries = []
        self.file_path = os.path.join(
            os.path.expanduser("~"), ".quick-translate", "history.json")
        self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.entries = data[:self.max_size]
            except Exception:
                pass

    def _save(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, ensure_ascii=False, indent=None)

    def add(self, word: str, definition: str = ""):
        """添加一条查询记录"""
        word = word.strip().lower()
        if not word:
            return

        # 去重（移到最前面）
        self.entries = [e for e in self.entries if e.get("word") != word]

        # 插入到最前面
        self.entries.insert(0, {
            "word": word,
            "definition": definition.split("\n")[0][:80],  # 只保存第一行释义
            "time": datetime.now().strftime("%m-%d %H:%M"),
        })

        # 限制大小
        self.entries = self.entries[:self.max_size]
        self._save()

    def get_recent(self, limit=10) -> list:
        """获取最近的查询记录"""
        return self.entries[:limit]

    def clear(self):
        """清空历史"""
        self.entries = []
        self._save()

    def search(self, query: str, limit=5) -> list:
        """在历史中搜索"""
        q = query.lower()
        return [e for e in self.entries if q in e.get("word", "")][:limit]
