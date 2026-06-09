"""MDX dictionary reader — reads Eudic MDX files via SQLite cache.

Builds a SQLite database from the MDX export on first run,
then uses SQLite for instant lookups. Preserves original HTML
for rich display with phonetics, definitions, and examples.
"""
from __future__ import annotations
import os
import re
import html as html_mod
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Optional, List, Dict

from ...utils.logging import logger


class MDXDictionary:
    """Read MDX dictionary files with SQLite caching.

    Workflow:
    1. First run: `mdict -x` exports to .txt, then parse into SQLite
    2. Subsequent runs: load SQLite directly (~0.1ms per lookup)
    """

    def __init__(self, mdx_path: str, db_path: str | None = None) -> None:
        self._mdx_path = mdx_path
        self._db_path = db_path or mdx_path.rsplit('.', 1)[0] + '.db'
        self._conn: Optional[sqlite3.Connection] = None
        self._ready = False
        self._word_count = 0

    def initialize(self) -> None:
        """Load or build the SQLite database."""
        if os.path.exists(self._db_path):
            # Check if DB is newer than MDX
            mdx_mtime = os.path.getmtime(self._mdx_path)
            db_mtime = os.path.getmtime(self._db_path)
            if db_mtime >= mdx_mtime:
                self._load_db()
                return
            else:
                logger.info("MDX file updated, rebuilding SQLite cache...")

        self._build_db()

    def _load_db(self) -> None:
        """Load existing SQLite database."""
        t0 = time.perf_counter()
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA cache_size=-8000")  # 8MB cache
        row = self._conn.execute("SELECT COUNT(*) FROM entries").fetchone()
        self._word_count = row[0]
        self._ready = True
        elapsed = (time.perf_counter() - t0) * 1000
        logger.info("MDX SQLite loaded: {} words in {:.0f}ms", self._word_count, elapsed)

    def _build_db(self) -> None:
        """Build SQLite database from MDX file."""
        t0 = time.perf_counter()

        # Step 1: Export MDX to text
        export_dir = Path(self._db_path).parent / "mdx_export"
        export_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Exporting MDX to text...")
        result = subprocess.run(
            ["mdict", "-x", self._mdx_path, "-d", str(export_dir)],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            logger.error("MDX export failed: {}", result.stderr)
            return

        # Find the .txt file
        txt_files = list(export_dir.glob("*.txt"))
        if not txt_files:
            logger.error("No .txt file found in export")
            return
        txt_path = txt_files[0]

        t1 = time.perf_counter()
        logger.info("MDX exported in {:.0f}ms, parsing...", (t1 - t0) * 1000)

        # Step 2: Parse and insert into SQLite
        conn = sqlite3.connect(self._db_path)
        conn.execute("DROP TABLE IF EXISTS entries")
        conn.execute("""CREATE TABLE entries (
            word TEXT PRIMARY KEY,
            html TEXT NOT NULL,
            phonetic TEXT,
            pos TEXT,
            definition TEXT
        )""")

        count = 0
        with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
            key = None
            content_lines: list[str] = []
            for line in f:
                line = line.rstrip("\r\n")
                if line == "</>":
                    if key and content_lines:
                        html_content = "\n".join(content_lines)
                        phon, pos, defn = self._extract_metadata(html_content)
                        conn.execute(
                            "INSERT OR REPLACE INTO entries VALUES (?,?,?,?,?)",
                            (key.lower(), html_content, phon, pos, defn),
                        )
                        count += 1
                        if count % 50000 == 0:
                            conn.commit()
                    key = None
                    content_lines = []
                elif key is None:
                    key = line
                else:
                    content_lines.append(line)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_word ON entries(word)")
        conn.commit()

        t2 = time.perf_counter()
        self._word_count = count
        logger.info("MDX SQLite built: {} words in {:.0f}ms", count, (t2 - t0) * 1000)

        conn.close()
        self._load_db()

    @staticmethod
    def _extract_metadata(html_content: str) -> tuple[str, str, str]:
        """Extract phonetic, POS, and first Chinese definition from HTML."""
        phon = ""
        m = re.search(r'<span class="phon">(.*?)</span>', html_content)
        if m:
            phon = html_mod.unescape(m.group(1))

        pos = ""
        m = re.search(r'<span\s+class="pos"[^>]*>(.*?)</span>', html_content, re.DOTALL)
        if m:
            pos = html_mod.unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip())
            pos = re.sub(r"[,\s]+$", "", pos).strip()  # clean trailing commas

        defn = ""
        m = re.search(r"<defT><chn>(.*?)</chn></defT>", html_content)
        if m:
            defn = html_mod.unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip())

        return phon, pos, defn

    @staticmethod
    def html_to_text(html_content: str) -> str:
        """Convert MDX HTML to readable plain text for display.

        Extracts: headword, phonetic, POS, definitions, examples with translations.
        """
        lines: list[str] = []

        # Headword
        m = re.search(r'<h1 class="headword"[^>]*>(.*?)</h1>', html_content)
        if m:
            lines.append(m.group(1).strip())

        # Phonetic
        phons = re.findall(r'<span class="phon">(.*?)</span>', html_content)
        if phons:
            lines.append("  " + "  ".join(phons))

        # POS
        m = re.search(r'<span class="pos">(.*?)</span>', html_content)
        if m:
            pos = re.sub(r"<[^>]+>", " ", m.group(1)).strip()
            pos = re.sub(r"\s+", " ", pos)
            lines.append(f"  {pos}")

        # Senses (definitions + examples)
        senses = re.finditer(
            r'<li class="sense"[^>]*>(.*?)</li>',
            html_content, re.DOTALL,
        )
        sense_num = 0
        for sense_match in senses:
            sense_html = sense_match.group(1)
            sense_num += 1

            # Labels (e.g., "informal", "British English")
            labels = re.findall(r'<span class="labels"[^>]*>(.*?)</span>', sense_html)
            label_str = ""
            if labels:
                label_str = re.sub(r"<[^>]+>", "", labels[0]).strip()

            # Definition (English)
            defn_en = ""
            m = re.search(r'<span class="def"[^>]*>(.*?)</span>', sense_html, re.DOTALL)
            if m:
                defn_en = re.sub(r"<[^>]+>", "", m.group(1)).strip()
                defn_en = re.sub(r"\s+", " ", defn_en)

            # Definition (Chinese)
            defn_zh = ""
            m = re.search(r"<defT><chn>(.*?)</chn></defT>", sense_html)
            if m:
                defn_zh = html_mod.unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip())

            if defn_en or defn_zh:
                prefix = f"  {sense_num}."
                if label_str:
                    prefix += f" [{label_str}]"
                lines.append(prefix)
                if defn_en:
                    lines.append(f"     {defn_en}")
                if defn_zh:
                    lines.append(f"     {defn_zh}")

            # Examples
            examples = re.finditer(
                r'<span class="x">(.*?)</span>.*?<xT><chn>(.*?)</chn></xT>',
                sense_html, re.DOTALL,
            )
            for ex_match in examples:
                ex_en = re.sub(r"<[^>]+>", "", ex_match.group(1)).strip()
                ex_zh = html_mod.unescape(re.sub(r"<[^>]+>", "", ex_match.group(2)).strip())
                if ex_en:
                    lines.append(f"     例: {ex_en}")
                if ex_zh:
                    lines.append(f"       {ex_zh}")

        return "\n".join(lines)

    def lookup(self, word: str) -> Optional[Dict[str, str]]:
        """Look up a word. Returns dict with word, html, phonetic, pos, definition, text."""
        if not self._ready or not self._conn:
            return None
        row = self._conn.execute(
            "SELECT word, html, phonetic, pos, definition FROM entries WHERE word=?",
            (word.lower(),),
        ).fetchone()
        if not row:
            return None
        return {
            "word": row[0],
            "html": row[1],
            "phonetic": row[2] or "",
            "pos": row[3] or "",
            "definition": row[4] or "",
            "text": self.html_to_text(row[1]),
        }

    def search_prefix(self, prefix: str, limit: int = 20) -> List[Dict[str, str]]:
        """Prefix search."""
        if not self._ready or not self._conn:
            return []
        rows = self._conn.execute(
            "SELECT word, phonetic, pos, definition FROM entries WHERE word LIKE ? LIMIT ?",
            (prefix.lower() + "%", limit),
        ).fetchall()
        return [
            {"word": r[0], "phonetic": r[1] or "", "pos": r[2] or "", "definition": r[3] or ""}
            for r in rows
        ]

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def word_count(self) -> int:
        return self._word_count
