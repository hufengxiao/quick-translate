"""查词统计 - 记录每日/每周查词数量"""
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta


class SearchStats:
    """查词统计，保存到 ~/.quick-translate/stats.json

    存储格式：
    {
        "daily": {"2024-01-15": 42, "2024-01-16": 17, ...},
        "words": {"hello": 5, "world": 3, ...}  -- 按查词次数排序
    }
    """

    def __init__(self, max_days=365):
        self.max_days = max_days
        self.daily = {}  # {"YYYY-MM-DD": count}
        self.words = {}  # {"word": total_count}
        self.file_path = os.path.join(
            os.path.expanduser("~"), ".quick-translate", "stats.json")
        self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.daily = data.get("daily", {})
                self.words = data.get("words", {})
                # Trim old days
                if len(self.daily) > self.max_days:
                    sorted_days = sorted(self.daily.keys())
                    for old_day in sorted_days[:-self.max_days]:
                        del self.daily[old_day]
            except Exception:
                pass

    def _save(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump({"daily": self.daily, "words": self.words},
                      f, ensure_ascii=False, indent=None)

    def record(self, word: str):
        """记录一次查词"""
        word = word.strip().lower()
        if not word:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        self.daily[today] = self.daily.get(today, 0) + 1
        self.words[word] = self.words.get(word, 0) + 1
        self._save()

    def get_today_count(self) -> int:
        """获取今日查词数量"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.daily.get(today, 0)

    def get_daily_stats(self, days: int = 7) -> list:
        """获取最近 N 天的每日查词统计

        Returns:
            list of {"date": "YYYY-MM-DD", "count": int}, 从旧到新排序
        """
        result = []
        now = datetime.now()
        for i in range(days - 1, -1, -1):
            d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            result.append({"date": d, "count": self.daily.get(d, 0)})
        return result

    def get_weekly_stats(self, weeks: int = 4) -> list:
        """获取最近 N 周的每周查词统计

        Returns:
            list of {"week_start": "YYYY-MM-DD", "week_end": "YYYY-MM-DD", "count": int}
            从旧到新排序，每周从周一开始
        """
        now = datetime.now()
        result = []
        for i in range(weeks - 1, -1, -1):
            # Calculate the Monday of the target week
            today_weekday = now.weekday()  # 0=Monday
            week_start = now - timedelta(days=today_weekday + 7 * i)
            week_end = week_start + timedelta(days=6)
            count = 0
            for d in range(7):
                day_str = (week_start + timedelta(days=d)).strftime("%Y-%m-%d")
                count += self.daily.get(day_str, 0)
            result.append({
                "week_start": week_start.strftime("%Y-%m-%d"),
                "week_end": week_end.strftime("%Y-%m-%d"),
                "count": count,
            })
        return result

    def get_total_count(self) -> int:
        """获取总查词数量"""
        return sum(self.daily.values())

    def get_top_words(self, limit: int = 10) -> list:
        """获取查询次数最多的单词

        Returns:
            list of {"word": str, "count": int}，按次数降序
        """
        sorted_words = sorted(self.words.items(), key=lambda x: x[1], reverse=True)
        return [{"word": w, "count": c} for w, c in sorted_words[:limit]]

    def get_unique_word_count(self) -> int:
        """获取去重后的查词数量"""
        return len(self.words)

    def clear(self):
        """清空所有统计数据"""
        self.daily = {}
        self.words = {}
        self._save()
