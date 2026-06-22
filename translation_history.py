"""AI 翻译历史管理 - 持久化保存 AI 翻译结果"""
import json
import os
import threading
from datetime import datetime


class TranslationHistory:
    """AI 翻译历史，保存到 ~/.quick-translate/translation_history.json

    存储 AI 翻译的源文本和结果，方便用户回顾之前的翻译。
    """

    def __init__(self, max_size=200):
        self.max_size = max_size
        self.entries = []
        self.file_path = os.path.join(
            os.path.expanduser("~"), ".quick-translate", "translation_history.json")
        self._lock = threading.Lock()
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
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.entries, f, ensure_ascii=False, indent=None)
        except Exception:
            pass

    def add(self, source: str, result: str, model: str = ""):
        """添加一条翻译记录（线程安全）

        Args:
            source: 原文
            result: AI 翻译结果
            model: 使用的模型名称（可选）
        """
        source = source.strip()
        if not source:
            return

        with self._lock:
            # 去重（移到最前面）
            self.entries = [e for e in self.entries if e.get("source") != source]

            # 插入到最前面
            entry = {
                "source": source,
                "result": result.strip(),
                "time": datetime.now().strftime("%m-%d %H:%M"),
            }
            if model:
                entry["model"] = model
            self.entries.insert(0, entry)

            # 限制大小
            self.entries = self.entries[:self.max_size]
            self._save()

    def get_recent(self, limit=10) -> list:
        """获取最近的翻译记录"""
        with self._lock:
            return self.entries[:limit]

    def search(self, query: str, limit=5) -> list:
        """在翻译历史中搜索（匹配源文本或结果）"""
        q = query.lower()
        with self._lock:
            return [
                e for e in self.entries
                if q in e.get("source", "").lower() or q in e.get("result", "").lower()
            ][:limit]

    def clear(self):
        """清空翻译历史"""
        with self._lock:
            self.entries = []
            self._save()

    @property
    def count(self) -> int:
        """当前记录数"""
        return len(self.entries)
