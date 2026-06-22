"""生词本管理 - 一键收藏单词到本地生词本"""
import csv
import io
import json
import os
from datetime import datetime


class VocabularyBook:
    """生词本，保存到 ~/.quick-translate/vocabulary.json"""

    def __init__(self, max_size=500):
        self.max_size = max_size
        self.entries = []
        self.file_path = os.path.join(
            os.path.expanduser("~"), ".quick-translate", "vocabulary.json")
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
        """收藏一个单词到生词本"""
        word = word.strip()
        if not word:
            return
        # 如果已存在，保留其星标状态，先移除再重新添加（刷新时间）
        existing_starred = any(
            e.get("word") == word and e.get("starred") for e in self.entries
        )
        self.entries = [e for e in self.entries if e.get("word") != word]
        self.entries.insert(0, {
            "word": word,
            "definition": definition.split("\n")[0][:120],
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "starred": existing_starred,
        })
        self.entries = self.entries[:self.max_size]
        self._save()

    def remove(self, word: str):
        """从生词本移除一个单词"""
        word = word.strip()
        before = len(self.entries)
        self.entries = [e for e in self.entries if e.get("word") != word]
        if len(self.entries) < before:
            self._save()

    def is_favorited(self, word: str) -> bool:
        """检查单词是否已在生词本中"""
        word = word.strip()
        return any(e.get("word") == word for e in self.entries)

    def toggle(self, word: str, definition: str = "") -> bool:
        """切换收藏状态。返回 True 表示已收藏，False 表示已取消收藏。"""
        if self.is_favorited(word):
            self.remove(word)
            return False
        else:
            self.add(word, definition)
            return True

    def toggle_star(self, word: str) -> bool:
        """切换星标状态。返回 True 表示已星标，False 表示已取消星标。

        单词必须已在生词本中才能加星标。
        """
        word = word.strip()
        for e in self.entries:
            if e.get("word") == word:
                e["starred"] = not e.get("starred", False)
                self._save()
                return e["starred"]
        return False

    def is_starred(self, word: str) -> bool:
        """检查单词是否已星标"""
        word = word.strip()
        return any(e.get("word") == word and e.get("starred") for e in self.entries)

    def get_all(self, limit: int = 100) -> list:
        """获取所有收藏的单词（星标词汇置顶）"""
        starred = [e for e in self.entries if e.get("starred")]
        unstarred = [e for e in self.entries if not e.get("starred")]
        return (starred + unstarred)[:limit]

    def clear(self):
        """清空生词本"""
        self.entries = []
        self._save()

    def search(self, query: str, limit: int = 10) -> list:
        """在生词本中搜索（星标词汇置顶）"""
        q = query.lower()
        results = [e for e in self.entries if q in e.get("word", "").lower()]
        starred = [e for e in results if e.get("starred")]
        unstarred = [e for e in results if not e.get("starred")]
        return (starred + unstarred)[:limit]

    def export_csv(self) -> str:
        """导出为 CSV 格式字符串"""
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Word", "Definition", "Added"])
        for e in self.entries:
            writer.writerow([
                e.get("word", ""),
                e.get("definition", ""),
                e.get("time", ""),
            ])
        return buf.getvalue()

    def export_anki(self) -> str:
        """导出为 Anki TSV 格式（可直接导入 Anki）"""
        lines = []
        for e in self.entries:
            word = e.get("word", "")
            definition = e.get("definition", "").replace("\t", " ")
            # Anki 用 tab 分隔 front 和 back
            lines.append(f"{word}\t{definition}")
        return "\n".join(lines)

    def export_to_file(self, path: str, fmt: str = "csv") -> str:
        """导出到文件。fmt 可选 'csv' 或 'anki'。返回实际写入的文件路径。"""
        if fmt == "anki":
            content = self.export_anki()
            if not path.endswith(".txt"):
                path = path.rsplit(".", 1)[0] + ".txt" if "." in path else path + ".txt"
        else:
            content = self.export_csv()
            if not path.endswith(".csv"):
                path = path.rsplit(".", 1)[0] + ".csv" if "." in path else path + ".csv"
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def random_quiz(self, num_choices: int = 4) -> dict:
        """随机抽取生词生成测试题。

        Returns a dict with:
            question_word: str — the word to quiz on
            question_definition: str — the definition shown as the prompt
            correct_word: str — the correct word (same as question_word)
            choices: list[str] — shuffled list of word choices (includes correct)
            answer_index: int — index of the correct answer in choices
        Returns None if vocabulary has fewer than 2 entries.
        """
        import random
        if len(self.entries) < 2:
            return None
        # Pick a random entry as the question
        entry = random.choice(self.entries)
        word = entry.get("word", "")
        definition = entry.get("definition", "")
        if not word:
            return None
        # Pick distractors (other words)
        other_words = [e["word"] for e in self.entries if e.get("word") != word]
        num_distractors = min(num_choices - 1, len(other_words))
        distractors = random.sample(other_words, num_distractors)
        # Build choices and shuffle
        choices = [word] + distractors
        random.shuffle(choices)
        answer_index = choices.index(word)
        return {
            "question_word": word,
            "question_definition": definition,
            "correct_word": word,
            "choices": choices,
            "answer_index": answer_index,
        }

    def random_review(self, count: int = 10) -> list:
        """随机抽取多个生词生成一组测试题。

        Args:
            count: number of quiz questions to generate (max = len(entries))

        Returns:
            list of quiz dicts (same format as random_quiz)
        """
        import random
        if len(self.entries) < 2:
            return []
        actual_count = min(count, len(self.entries))
        # Pick unique words for the review session
        sampled = random.sample(self.entries, actual_count)
        quizzes = []
        seen_words = set()
        for entry in sampled:
            word = entry.get("word", "")
            if not word or word in seen_words:
                continue
            seen_words.add(word)
            # Build a quiz for this word
            other_words = [e["word"] for e in self.entries if e.get("word") != word]
            num_distractors = min(3, len(other_words))
            if num_distractors == 0:
                continue
            distractors = random.sample(other_words, num_distractors)
            choices = [word] + distractors
            random.shuffle(choices)
            quizzes.append({
                "question_word": word,
                "question_definition": entry.get("definition", ""),
                "correct_word": word,
                "choices": choices,
                "answer_index": choices.index(word),
            })
        return quizzes

    @property
    def count(self) -> int:
        return len(self.entries)
