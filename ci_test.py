"""CI test script — run all critical tests."""
import sys
import os
import time

sys.path.insert(0, ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from src.utils.logging import setup_logging

setup_logging("WARNING", False)

errors = []


def test(name, fn):
    try:
        fn()
        print(f"  PASS {name}")
    except Exception as e:
        errors.append(name)
        print(f"  FAIL {name}: {e}")


# 1. Config
def test_config():
    from src.utils.config import load_config, save_config
    cfg = load_config()
    assert cfg.ui.width > 0
    assert cfg.hotkey.key == "m"
    old = cfg.ui.width
    cfg.ui.width = 777
    save_config(cfg)
    cfg2 = load_config()
    assert cfg2.ui.width == 777
    cfg.ui.width = old
    save_config(cfg)


# 2. Errors
def test_errors():
    from src.utils.errors import (
        TranslateError, DictionaryNotFoundError, NetworkError,
        APIError, ConfigError, CacheError,
    )
    assert TranslateError("t").recoverable is True
    assert TranslateError("t", recoverable=False).recoverable is False
    assert DictionaryNotFoundError("d").recoverable is False
    assert NetworkError("n").recoverable is True
    assert APIError("a", status_code=429).status_code == 429
    assert ConfigError("c").recoverable is False


# 3. ExactIndex
def test_exact():
    from src.core.index.exact import ExactIndex
    idx = ExactIndex()
    idx.load({"hello": "hi", "world": "world"})
    assert idx.lookup("hello") == "hi"
    assert idx.lookup("none") is None
    assert idx.has("hello") and not idx.has("none")
    assert idx.size == 2


# 4. TrieIndex
def test_trie():
    from src.core.index.trie import TrieIndex
    t = TrieIndex()
    t.insert("apple", "n.apple")
    t.insert("application", "n.app")
    t.insert("apply", "v.apply")
    t.insert("banana", "n.banana")
    r = t.search_prefix("app", 10)
    assert len(r) == 3 and r[0]["word"] == "apple"
    r2 = t.search_prefix("xyz", 10)
    assert len(r2) == 0


# 5. BK-Tree
def test_bktree():
    from src.core.index.bktree import BKTree, levenshtein
    assert levenshtein("kitten", "sitting") == 3
    assert levenshtein("hello", "hallo") == 1
    assert levenshtein("", "") == 0
    tree = BKTree()
    for w, d in {"hello": "hi", "help": "aid", "world": "earth"}.items():
        tree.insert(w, d)
    r = tree.search("helo", tolerance=1, limit=5)
    found = [x["word"] for x in r]
    assert "hello" in found, f"hello not in {found}"


# 6. LRU Cache
def test_lru():
    from src.core.cache.lru import LRUCache
    import threading
    c = LRUCache(3)
    c.put("a", [{"word": "a"}])
    c.put("b", [{"word": "b"}])
    c.put("c", [{"word": "c"}])
    c.put("d", [{"word": "d"}])  # evicts a
    assert c.get("a") is None
    assert c.get("d") is not None
    # Concurrent
    c2 = LRUCache(100)
    errs = []

    def w():
        for i in range(100):
            try:
                c2.put(f"w{i}", [{"word": f"w{i}"}])
            except Exception as e:
                errs.append(e)

    def r():
        for i in range(100):
            try:
                c2.get(f"w{i}")
            except Exception as e:
                errs.append(e)

    ts = [threading.Thread(target=w), threading.Thread(target=r)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not errs


# 7. Dictionary (full integration)
def test_dictionary():
    from src.utils.config import load_config
    from src.core.dict.dictionary import Dictionary
    cfg = load_config()
    dp = cfg.dictionary.dict_path
    if not os.path.isabs(dp):
        dp = os.path.join(".", dp)
    assert os.path.exists(dp), f"Dict not found: {dp}"
    d = Dictionary(dp, 10000, 500)
    d.load()
    time.sleep(1)
    r = d.search("hello")
    assert len(r) > 0 and r[0]["word"] == "hello", f"hello search failed: {r}"
    r2 = d.search("trans")
    assert len(r2) > 0
    r3 = d.search("")
    assert len(r3) == 0


# 7b. Spell correction
def test_spell_correction():
    from dictionary import _levenshtein, Dictionary
    # Test levenshtein function
    assert _levenshtein("hello", "hello") == 0
    assert _levenshtein("hello", "helllo") == 1  # extra 'l'
    assert _levenshtein("hello", "helo") == 1    # missing 'l'
    assert _levenshtein("hello", "hallo") == 1   # substitution
    assert _levenshtein("hello", "world") == 4   # very different
    assert _levenshtein("", "abc") == 3
    assert _levenshtein("abc", "") == 3
    assert _levenshtein("", "") == 0
    # Test spell correction on Dictionary
    from src.utils.config import load_config
    cfg = load_config()
    dp = cfg.dictionary.dict_path
    if not os.path.isabs(dp):
        dp = os.path.join(".", dp)
    d = Dictionary(dp)
    # "helllo" should find "hello" within edit distance 2
    results = d.search_spell("helllo", tolerance=2, limit=5)
    words = [r["word"] for r in results]
    assert "hello" in words, f"'hello' not in spell results for 'helllo': {words}"
    # "wrold" should find "world" within edit distance 2 (needs higher limit, many dist-2 words)
    results2 = d.search_spell("wrold", tolerance=2, limit=50)
    words2 = [r["word"] for r in results2]
    assert "world" in words2, f"'world' not in spell results for 'wrold': {words2}"
    # Integration: search_fuzzy should fall back to spell correction
    results3 = d.search_fuzzy("helllo", limit=5)
    words3 = [r["word"] for r in results3]
    assert "hello" in words3, f"'hello' not in fuzzy results for 'helllo': {words3}"


# 8. Theme
def test_theme():
    from src.ui.theme import DARK, LIGHT, HIGH_CONTRAST, get_theme
    assert DARK.bg == "#1C1C1E"
    assert LIGHT.bg == "#FFFFFF"
    assert HIGH_CONTRAST.bg == "#000000"
    assert get_theme("high_contrast") == HIGH_CONTRAST


# 9. Translator lock
def test_translator():
    from translator import AITranslator
    ai = AITranslator("http://localhost", "k", "m", "p")
    assert hasattr(ai, "_lock")


# 10. No TTS remnants
def test_no_tts():
    assert not os.path.exists("src/services/tts.py"), "tts.py still exists"
    with open("main.py") as f:
        assert "tts" not in f.read().lower()


# 11. Clipboard monitor import
def test_clipboard():
    from src.services.clipboard import ClipboardMonitor
    triggered = []
    mon = ClipboardMonitor(on_text=lambda t: triggered.append(t), auto_translate=False)
    assert not mon._running
    # Test should-ignore logic
    assert mon._should_ignore("") is True
    assert mon._should_ignore("a") is True
    assert mon._should_ignore("hello") is False
    assert mon._should_ignore("https://example.com") is True
    assert mon._should_ignore("123.45") is True


# 12. Config clipboard fields
def test_config_clipboard():
    from src.utils.config import load_config, save_config
    cfg = load_config()
    assert hasattr(cfg, 'clipboard')
    assert cfg.clipboard.monitor_enabled is False
    assert cfg.clipboard.min_length == 2


# 13. MDX path configurable
def test_mdx_path_config():
    from config import load_config, save_config
    cfg = load_config()
    assert "mdx_path" in cfg["dictionary"]
    assert "牛津" in cfg["dictionary"]["mdx_path"]


# 13b. Pinyin search
def test_pinyin_search():
    from dictionary import Dictionary
    from src.utils.config import load_config
    cfg = load_config()
    dp = cfg.dictionary.dict_path
    if not os.path.isabs(dp):
        dp = os.path.join(".", dp)
    assert os.path.exists(dp), f"Dict not found: {dp}"
    d = Dictionary(dp)
    # "nihao" should find "你好" via pinyin matching
    results = d.search_pinyin("nihao", limit=10)
    words = [r["word"] for r in results]
    assert "你好" in words, f"'你好' not in pinyin results for 'nihao': {words}"
    # Integration: search_fuzzy should fall back to pinyin
    results2 = d.search_fuzzy("nihao", limit=10)
    words2 = [r["word"] for r in results2]
    assert "你好" in words2, f"'你好' not in fuzzy results for 'nihao': {words2}"
    # "zhongguo" should find "中国"
    results3 = d.search_pinyin("zhongguo", limit=10)
    words3 = [r["word"] for r in results3]
    assert "中国" in words3, f"'中国' not in pinyin results for 'zhongguo': {words3}"
    # Empty / non-alpha queries should return nothing
    assert d.search_pinyin("") == []
    assert d.search_pinyin("123") == []


# 16. Relevance sorting: exact > prefix > contains
def test_relevance_sorting():
    from src.core.index.exact import ExactIndex
    from src.core.index.trie import TrieIndex
    from src.core.index.bktree import BKTree
    from src.core.index.router import QueryRouter
    from src.core.cache.lru import LRUCache

    exact = ExactIndex()
    trie = TrieIndex()
    cache = LRUCache(100)

    data = {
        "hello": "greeting",
        "helpful": "adj.useful",
        "helicopter": "n.flying machine",
        "shell": "n.covering",
        "othello": "n.play",
    }
    exact.load(data)
    trie.load(data)
    router = QueryRouter(
        exact=exact, trie=trie, cache=cache,
        bktree=BKTree(), pinyin_index=None,
        sorted_keys=sorted(data.keys()), raw_dict=data,
    )

    # Search "hello" — exact match should be first with match_type="exact"
    results = router.search("hello", limit=20)
    assert len(results) > 0, "No results for 'hello'"
    assert results[0]["word"] == "hello", f"Expected 'hello' first, got '{results[0]['word']}'"
    assert results[0]["match_type"] == "exact", f"Expected exact, got {results[0].get('match_type')}"

    # All results should have match_type
    for r in results:
        assert "match_type" in r, f"Missing match_type in result: {r}"

    # Search "hel" — prefix matches should all come before contains matches
    results2 = router.search("hel", limit=20)
    types = [r["match_type"] for r in results2]
    # exact first (if any), then prefix, then contains
    prefix_idx = next((i for i, t in enumerate(types) if t == "prefix"), len(types))
    contains_idx = next((i for i, t in enumerate(types) if t == "contains"), len(types))
    assert prefix_idx <= contains_idx, f"prefix({prefix_idx}) should come before contains({contains_idx}): {types}"

    # Contains-only search: "hello" appears in "othello" via contains
    results3 = router.search("hell", limit=20)
    types3 = [r["match_type"] for r in results3]
    # prefix matches (hello, helpful, helicopter) should come before contains (othello, shell)
    has_prefix = any(t == "prefix" for t in types3)
    has_contains = any(t == "contains" for t in types3)
    if has_prefix and has_contains:
        last_prefix = max(i for i, t in enumerate(types3) if t == "prefix")
        first_contains = min(i for i, t in enumerate(types3) if t == "contains")
        assert last_prefix < first_contains, \
            f"prefix results should come before contains: {list(zip(types3, [r['word'] for r in results3]))}"

    print("  PASS Relevance Sorting (via query)")


print("Running tests...")
test("Config", test_config)
test("Errors", test_errors)
test("ExactIndex", test_exact)
test("TrieIndex", test_trie)
test("BK-Tree", test_bktree)
test("LRU Cache", test_lru)
test("Dictionary", test_dictionary)
test("Spell Correction", test_spell_correction)
test("Theme", test_theme)
test("Translator", test_translator)
test("No TTS", test_no_tts)
test("Clipboard Monitor", test_clipboard)
test("Config Clipboard", test_config_clipboard)
test("MDX Path Config", test_mdx_path_config)
test("Pinyin Search", test_pinyin_search)
test("Relevance Sorting", test_relevance_sorting)


# 17. Vocabulary Book
def test_vocabulary():
    from vocabulary import VocabularyBook
    import tempfile, os
    # Use a temp file to avoid polluting real data
    tmpdir = tempfile.mkdtemp()
    tmpfile = os.path.join(tmpdir, "vocabulary.json")
    vb = VocabularyBook.__new__(VocabularyBook)
    vb.max_size = 500
    vb.entries = []
    vb.file_path = tmpfile

    # Add a word
    vb.add("hello", "你好")
    assert vb.count == 1
    assert vb.is_favorited("hello") is True
    assert vb.is_favorited("world") is False

    # Toggle off
    result = vb.toggle("hello", "你好")
    assert result is False
    assert vb.count == 0
    assert vb.is_favorited("hello") is False

    # Toggle on
    result = vb.toggle("world", "世界")
    assert result is True
    assert vb.count == 1

    # Add duplicate (moves to top)
    vb.add("hello", "你好")
    vb.add("hello", "你好 updated")
    assert vb.count == 2
    entries = vb.get_all()
    assert entries[0]["word"] == "hello"

    # Search
    r = vb.search("hel")
    assert len(r) == 1 and r[0]["word"] == "hello"

    # Remove
    vb.remove("hello")
    assert vb.count == 1
    assert vb.is_favorited("hello") is False

    # Clear
    vb.clear()
    assert vb.count == 0

    # Cleanup
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


test("Vocabulary Book", test_vocabulary)


# 18. Vocabulary Export
def test_vocabulary_export():
    from vocabulary import VocabularyBook
    import tempfile, os
    tmpdir = tempfile.mkdtemp()
    tmpfile = os.path.join(tmpdir, "vocabulary.json")
    vb = VocabularyBook.__new__(VocabularyBook)
    vb.max_size = 500
    vb.entries = []
    vb.file_path = tmpfile

    vb.add("hello", "你好")
    vb.add("world", "世界")
    vb.add("apple", "苹果")

    # CSV export
    csv_content = vb.export_csv()
    assert "Word,Definition,Added" in csv_content
    assert "hello" in csv_content
    assert "世界" in csv_content
    lines = csv_content.strip().split("\n")
    assert len(lines) == 4  # header + 3 entries

    # Anki export
    anki_content = vb.export_anki()
    assert "hello\t你好" in anki_content
    assert "world\t世界" in anki_content
    anki_lines = anki_content.strip().split("\n")
    assert len(anki_lines) == 3

    # Export to file (CSV)
    csv_path = os.path.join(tmpdir, "export.csv")
    returned = vb.export_to_file(csv_path, fmt="csv")
    assert returned.endswith(".csv")
    assert os.path.exists(returned)
    with open(returned, "r", encoding="utf-8") as f:
        assert "hello" in f.read()

    # Export to file (Anki) — auto-appends .txt
    anki_path = os.path.join(tmpdir, "export.txt")
    returned2 = vb.export_to_file(anki_path, fmt="anki")
    assert returned2.endswith(".txt")
    assert os.path.exists(returned2)
    with open(returned2, "r", encoding="utf-8") as f:
        content = f.read()
        assert "hello\t你好" in content

    # Auto-extension: if no .txt, Anki export should add it
    anki_path2 = os.path.join(tmpdir, "anki_export")
    returned3 = vb.export_to_file(anki_path2, fmt="anki")
    assert returned3.endswith(".txt")

    # Empty vocab export
    vb.clear()
    empty_csv = vb.export_csv()
    assert "Word,Definition,Added" in empty_csv
    assert len(empty_csv.strip().split("\n")) == 1  # header only
    empty_anki = vb.export_anki()
    assert empty_anki == ""

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


test("Vocabulary Export", test_vocabulary_export)


# 19. Vocabulary Review (random quiz)
def test_vocabulary_review():
    from vocabulary import VocabularyBook
    import tempfile, os
    tmpdir = tempfile.mkdtemp()
    tmpfile = os.path.join(tmpdir, "vocabulary.json")
    vb = VocabularyBook.__new__(VocabularyBook)
    vb.max_size = 500
    vb.entries = []
    vb.file_path = tmpfile

    # Too few entries — should return None / []
    vb.add("hello", "你好")
    assert vb.random_quiz() is None
    assert vb.random_review() == []

    # Add more words
    vb.add("world", "世界")
    vb.add("apple", "苹果")
    vb.add("banana", "香蕉")
    vb.add("cat", "猫")

    # random_quiz
    quiz = vb.random_quiz(num_choices=4)
    assert quiz is not None
    assert quiz["correct_word"] in [e["word"] for e in vb.entries]
    assert len(quiz["choices"]) == 4
    assert quiz["choices"][quiz["answer_index"]] == quiz["correct_word"]
    assert quiz["question_definition"] != ""

    # random_review
    reviews = vb.random_review(count=3)
    assert len(reviews) == 3
    for r in reviews:
        assert r["correct_word"] in [e["word"] for e in vb.entries]
        assert r["choices"][r["answer_index"]] == r["correct_word"]
        assert len(r["choices"]) >= 2  # at least correct + 1 distractor

    # random_review count > entries — should cap at entry count
    reviews2 = vb.random_review(count=100)
    assert len(reviews2) == 5  # only 5 entries

    # All quiz words should be unique in a review session
    quiz_words = [r["question_word"] for r in reviews2]
    assert len(quiz_words) == len(set(quiz_words))

    # Verify answer_index is valid for every quiz
    for r in reviews2:
        assert 0 <= r["answer_index"] < len(r["choices"])
        assert r["choices"][r["answer_index"]] == r["correct_word"]

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


test("Vocabulary Review", test_vocabulary_review)


# 20. Vocabulary Star (星标词汇)
def test_vocabulary_star():
    from vocabulary import VocabularyBook
    import tempfile, os
    tmpdir = tempfile.mkdtemp()
    tmpfile = os.path.join(tmpdir, "vocabulary.json")
    vb = VocabularyBook.__new__(VocabularyBook)
    vb.max_size = 500
    vb.entries = []
    vb.file_path = tmpfile

    # Add some words
    vb.add("hello", "你好")
    vb.add("world", "世界")
    vb.add("apple", "苹果")
    vb.add("banana", "香蕉")

    # Initially none starred
    assert vb.is_starred("hello") is False
    assert vb.is_starred("world") is False

    # Star a word
    result = vb.toggle_star("hello")
    assert result is True
    assert vb.is_starred("hello") is True

    # Star another word
    vb.toggle_star("apple")
    assert vb.is_starred("apple") is True

    # get_all should return starred words first
    all_words = vb.get_all()
    # Starred items come first (apple was added after hello, so apple appears first in entries)
    starred_words = [w["word"] for w in all_words if w.get("starred")]
    unstarred_words = [w["word"] for w in all_words if not w.get("starred")]
    assert "hello" in starred_words
    assert "apple" in starred_words
    assert len(starred_words) == 2
    # Starred come before unstarred
    first_unstarred_idx = next(i for i, w in enumerate(all_words) if not w.get("starred"))
    for i in range(first_unstarred_idx):
        assert all_words[i].get("starred"), f"Word at {i} should be starred"
    assert "world" in unstarred_words
    assert "banana" in unstarred_words

    # search should return starred words first
    search_results = vb.search("a")
    starred_in_search = [r for r in search_results if r.get("starred")]
    unstarred_in_search = [r for r in search_results if not r.get("starred")]
    # apple should be before banana (starred first)
    words_in_order = [r["word"] for r in search_results]
    if "apple" in words_in_order and "banana" in words_in_order:
        assert words_in_order.index("apple") < words_in_order.index("banana")

    # Unstar
    result = vb.toggle_star("hello")
    assert result is False
    assert vb.is_starred("hello") is False

    # Starring a word not in vocab should return False
    assert vb.toggle_star("nonexistent") is False

    # Star should persist across add (re-add same word)
    vb.toggle_star("world")  # star world
    assert vb.is_starred("world") is True
    vb.add("world", "世界 updated")  # re-add
    assert vb.is_starred("world") is True  # star should persist

    # Export CSV should still work (backward compatible)
    csv_content = vb.export_csv()
    assert "Word,Definition,Added" in csv_content
    assert "hello" in csv_content

    # Verify entries have starred field
    for entry in vb.entries:
        assert "starred" in entry

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


test("Vocabulary Star", test_vocabulary_star)


# 21. Search Stats (查词统计)
def test_search_stats():
    from stats import SearchStats
    import tempfile, os, shutil
    tmpdir = tempfile.mkdtemp()
    tmpfile = os.path.join(tmpdir, "stats.json")
    ss = SearchStats.__new__(SearchStats)
    ss.max_days = 365
    ss.daily = {}
    ss.words = {}
    ss.file_path = tmpfile

    # Initially empty
    assert ss.get_today_count() == 0
    assert ss.get_total_count() == 0
    assert ss.get_unique_word_count() == 0

    # Record some lookups
    ss.record("hello")
    ss.record("world")
    ss.record("hello")

    assert ss.get_today_count() == 3
    assert ss.get_total_count() == 3
    assert ss.get_unique_word_count() == 2

    # Top words
    top = ss.get_top_words(limit=5)
    assert len(top) == 2
    assert top[0]["word"] == "hello"
    assert top[0]["count"] == 2
    assert top[1]["word"] == "world"
    assert top[1]["count"] == 1

    # Daily stats (should have today with count 3)
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    daily = ss.get_daily_stats(days=3)
    assert len(daily) == 3
    today_entry = [d for d in daily if d["date"] == today]
    assert len(today_entry) == 1
    assert today_entry[0]["count"] == 3

    # Weekly stats
    weekly = ss.get_weekly_stats(weeks=2)
    assert len(weekly) == 2
    # This week should have our 3 records
    this_week = weekly[-1]
    assert this_week["count"] == 3
    # Dates should be valid
    datetime.strptime(this_week["week_start"], "%Y-%m-%d")
    datetime.strptime(this_week["week_end"], "%Y-%m-%d")

    # Empty word should be ignored
    ss.record("")
    ss.record("   ")
    assert ss.get_total_count() == 3  # unchanged

    # Case insensitive
    ss.record("Hello")
    assert ss.words["hello"] == 3  # merged with existing

    # Clear
    ss.clear()
    assert ss.get_today_count() == 0
    assert ss.get_total_count() == 0

    # Simulate multi-day data
    from datetime import timedelta
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    ss.daily[yesterday] = 10
    ss.daily[today] = 5
    ss.words = {"test": 15}
    daily2 = ss.get_daily_stats(days=2)
    assert daily2[0]["date"] == yesterday
    assert daily2[0]["count"] == 10
    assert daily2[1]["date"] == today
    assert daily2[1]["count"] == 5

    shutil.rmtree(tmpdir, ignore_errors=True)


test("Search Stats", test_search_stats)


# 14. Startup benchmark
def test_startup():
    import subprocess
    # Cold startup (no .db cache)
    t0 = time.perf_counter()
    r = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0,'.');"
         "from dictionary import Dictionary;"
         "d = Dictionary('data/dict/ecdict.json');"
         "print(f'words={d.word_count}')"],
        capture_output=True, text=True, timeout=10, cwd=".",
    )
    elapsed = (time.perf_counter() - t0) * 1000
    assert r.returncode == 0, f"Startup failed: {r.stderr}"
    assert "words=" in r.stdout
    print(f"  JSON dict startup: {elapsed:.0f}ms")
    assert elapsed < 5000, f"Startup too slow: {elapsed:.0f}ms > 5000ms"


test("Startup", test_startup)


# 15. Query performance
def test_query_perf():
    from src.core.dict.mdx_dict import MDXDictionary
    mdx_path = "data/dict/牛津高阶第10版英汉双解V132/牛津高阶第10版英汉双解V132.mdx"
    if not os.path.exists(mdx_path):
        print("  MDX not found, skipping")
        return
    mdx = MDXDictionary(mdx_path)
    mdx.initialize()
    import timeit
    t = timeit.timeit(lambda: mdx.lookup("hello"), number=100) / 100 * 1000
    print(f"  MDX exact lookup: {t:.2f}ms")
    assert t < 50.0, f"Lookup too slow: {t:.2f}ms > 50ms"
    t2 = timeit.timeit(lambda: mdx.search_prefix("trans", 10), number=100) / 100 * 1000
    print(f"  MDX prefix search: {t2:.2f}ms")
    assert t2 < 15.0, f"Prefix too slow: {t2:.2f}ms > 15ms"


test("Query Perf", test_query_perf)


# 22. Multi-monitor position clamping
def test_monitor_clamp():
    from src.utils.monitor import get_monitor_rects, point_on_monitor, clamp_position, window_visible_on_monitor
    # Should return at least one monitor (even on CI)
    rects = get_monitor_rects()
    assert len(rects) >= 1, f"Expected >= 1 monitor, got {len(rects)}"
    # Each rect should be (left, top, right, bottom)
    for r in rects:
        assert len(r) == 4
        l, t, ri, b = r
        assert ri > l and b > t, f"Invalid monitor rect: {r}"
    # Point at 0,0 should be on monitor (primary)
    assert point_on_monitor(0, 0, rects) is True
    # Point at -99999,-99999 should not be on any monitor
    assert point_on_monitor(-99999, -99999, rects) is False
    # clamp_position with valid coords should return same coords
    l, t, ri, b = rects[0]
    cx, cy = l + 100, t + 100
    assert clamp_position(cx, cy, 400, 300, rects) == (cx, cy)
    # clamp_position with off-screen coords should move to primary monitor
    nx, ny = clamp_position(-99999, -99999, 400, 300, rects)
    assert nx >= l and ny >= t, f"Clamped position still off-screen: ({nx}, {ny})"
    # window_visible_on_monitor with valid position
    assert window_visible_on_monitor(cx, cy, 400, 300, rects) is True
    # window_visible_on_monitor with far off-screen
    assert window_visible_on_monitor(-99999, -99999, 400, 300, rects) is False


test("Multi-Monitor", test_monitor_clamp)


# 24. Multi AI Translator
def test_multi_translator():
    from translator import AITranslator, MultiAITranslator
    from src.utils.config import AIProvider, AIConfig

    # Single provider (backward compat)
    ai = AITranslator("http://localhost", "k", "m", "p")
    assert ai.is_configured
    assert ai.name == "m"

    # MultiAITranslator with no providers should not be configured
    multi = MultiAITranslator(providers=[], system_prompt="test")
    assert not multi.is_configured
    assert multi.provider_count == 0

    # MultiAITranslator with providers
    p1 = AIProvider(name="test1", api_base="http://localhost:1", api_key="k1", model="m1", priority=1)
    p2 = AIProvider(name="test2", api_base="http://localhost:2", api_key="k2", model="m2", priority=2)
    multi2 = MultiAITranslator(providers=[p1, p2], system_prompt="test")
    assert multi2.is_configured
    assert multi2.provider_count == 2
    assert multi2.get_provider_names() == ["test1", "test2"]
    assert multi2.current_provider_name == "test1"

    # Disabled provider should be excluded
    p3 = AIProvider(name="disabled", api_base="http://localhost:3", api_key="k3", model="m3", enabled=False)
    multi3 = MultiAITranslator(providers=[p1, p3], system_prompt="test")
    assert multi3.provider_count == 1
    assert multi3.get_provider_names() == ["test1"]

    # get_active_providers with explicit providers
    cfg = AIConfig()
    cfg.providers = [p1, p2]
    active = cfg.get_active_providers()
    assert len(active) == 2
    assert active[0].name == "test1"  # lower priority number first
    assert active[1].name == "test2"

    # get_active_providers legacy fallback (no providers, uses api_base)
    cfg2 = AIConfig(api_base="http://test", api_key="k", model="m")
    active2 = cfg2.get_active_providers()
    assert len(active2) == 1
    assert active2[0].name == "default"
    assert active2[0].api_base == "http://test"

    # get_active_providers with empty everything
    cfg3 = AIConfig(api_base="", api_key="", model="")
    cfg3.providers = []
    active3 = cfg3.get_active_providers()
    assert len(active3) == 0

    # Config dict with providers
    from src.utils.config import _dict_to_config
    d = {"ai": {"providers": [
        {"name": "a", "api_base": "http://a", "api_key": "ka", "model": "ma", "priority": 2},
        {"name": "b", "api_base": "http://b", "api_key": "kb", "model": "mb", "priority": 1},
    ], "auto_switch": False}}
    cfg4 = _dict_to_config(d)
    assert len(cfg4.ai.providers) == 2
    assert cfg4.ai.providers[0].name == "a"
    assert cfg4.ai.auto_switch is False


test("Multi AI Translator", test_multi_translator)


# 25. Translation Cache
def test_translation_cache():
    from translator import TranslationCache

    c = TranslationCache(max_size=3)
    assert c.get("hello") is None  # miss
    c.put("hello", "你好")
    assert c.get("hello") == "你好"  # hit
    assert c.size == 1
    assert c.stats()["hits"] == 1
    assert c.stats()["misses"] == 1

    # LRU eviction
    c.put("world", "世界")
    c.put("apple", "苹果")
    c.put("banana", "香蕉")  # evicts "hello"
    assert c.get("hello") is None
    assert c.get("banana") == "香蕉"
    assert c.size == 3

    # Thread safety
    import threading
    c2 = TranslationCache(100)
    errs = []

    def w():
        for i in range(100):
            try:
                c2.put(f"t{i}", f"r{i}")
            except Exception as e:
                errs.append(e)

    def r():
        for i in range(100):
            try:
                c2.get(f"t{i}")
            except Exception as e:
                errs.append(e)

    ts = [threading.Thread(target=w), threading.Thread(target=r)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not errs

    # Cache integration with AITranslator
    from translator import AITranslator
    ai = AITranslator("http://localhost", "k", "m", "p", cache_size=10)
    assert hasattr(ai, "_cache")
    assert isinstance(ai._cache, TranslationCache)

    # Cache integration with MultiAITranslator
    from translator import MultiAITranslator
    multi = MultiAITranslator(providers=[], system_prompt="test", cache_size=10)
    assert hasattr(multi, "_cache")
    assert isinstance(multi._cache, TranslationCache)

    # Clear
    c.clear()
    assert c.size == 0
    assert c.stats()["hits"] == 0


test("Translation Cache", test_translation_cache)


# 26. Translation History
def test_translation_history():
    import tempfile, shutil, threading
    from translation_history import TranslationHistory

    # Use a temp directory to avoid polluting real data
    tmp = tempfile.mkdtemp()
    try:
        # Monkey-patch file_path
        th = TranslationHistory.__new__(TranslationHistory)
        th.max_size = 5
        th.entries = []
        th.file_path = os.path.join(tmp, "translation_history.json")
        th._lock = threading.Lock()

        # Empty state
        assert th.count == 0
        assert th.get_recent() == []
        assert th.search("hello") == []

        # Add entries
        th.add("hello", "你好", model="gpt-4")
        assert th.count == 1
        entries = th.get_recent(1)
        assert entries[0]["source"] == "hello"
        assert entries[0]["result"] == "你好"
        assert entries[0]["model"] == "gpt-4"
        assert "time" in entries[0]

        th.add("world", "世界", model="claude")
        assert th.count == 2

        # Dedup: re-adding "hello" should move it to front
        th.add("hello", "你好 updated")
        assert th.count == 2
        entries = th.get_recent(2)
        assert entries[0]["source"] == "hello"
        assert entries[0]["result"] == "你好 updated"

        # Search by source
        results = th.search("world")
        assert len(results) == 1
        assert results[0]["source"] == "world"

        # Search by result
        results = th.search("你好")
        assert len(results) == 1
        assert results[0]["source"] == "hello"

        # Max size eviction
        th.add("a", "A")
        th.add("b", "B")
        th.add("c", "C")  # should evict oldest
        assert th.count == 5
        # "hello" (re-added most recently) should still be there
        sources = [e["source"] for e in th.get_recent(10)]
        assert "hello" in sources

        # Empty source should be ignored
        th.add("", "nothing")
        assert th.count == 5

        # Persistence: reload from file
        th2 = TranslationHistory.__new__(TranslationHistory)
        th2.max_size = 5
        th2.entries = []
        th2.file_path = th.file_path
        th2._lock = threading.Lock()
        th2._load()
        assert th2.count == th.count
        assert th2.entries[0]["source"] == th.entries[0]["source"]

        # Thread safety
        th3 = TranslationHistory.__new__(TranslationHistory)
        th3.max_size = 100
        th3.entries = []
        th3.file_path = os.path.join(tmp, "thread_test.json")
        th3._lock = threading.Lock()
        errs = []

        def writer():
            for i in range(50):
                try:
                    th3.add(f"word{i}", f"结果{i}")
                except Exception as e:
                    errs.append(e)

        def reader():
            for i in range(50):
                try:
                    th3.get_recent(5)
                    th3.search("word")
                except Exception as e:
                    errs.append(e)

        ts = [threading.Thread(target=writer), threading.Thread(target=reader)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        assert not errs, f"Thread errors: {errs}"
        assert th3.count == 50

        # Clear
        th.clear()
        assert th.count == 0
        assert th.get_recent() == []
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


test("Translation History", test_translation_history)


# 27. Word Root Analysis (词根分析)
def test_word_root():
    from word_root import analyze_word, format_analysis, PREFIXES, SUFFIXES, ROOTS

    # Basic prefix detection
    r = analyze_word("unhappy")
    assert r["prefix"] is not None, f"Should detect prefix 'un-' in 'unhappy': {r}"
    assert r["prefix"]["str"] == "un-", f"Expected 'un-', got {r['prefix']['str']}"

    # Suffix detection
    r2 = analyze_word("happiness")
    assert r2["suffix"] is not None, f"Should detect suffix in 'happiness': {r2}"
    assert "-ness" == r2["suffix"]["str"], f"Expected '-ness', got {r2['suffix']['str']}"

    # Root detection
    r3 = analyze_word("transport")
    assert r3["root"] is not None, f"Should detect root in 'transport': {r3}"
    assert r3["root"]["str"] == "port", f"Expected root 'port', got {r3['root']['str']}"
    assert "携带" in r3["root"]["meaning"], f"Root meaning should contain '携带': {r3['root']['meaning']}"

    # Combined: prefix + root + suffix
    r4 = analyze_word("uncomfortable")
    assert r4["prefix"] is not None, f"Should detect prefix in 'uncomfortable': {r4}"
    assert r4["suffix"] is not None, f"Should detect suffix in 'uncomfortable': {r4}"
    assert r4["prefix"]["str"] == "un-"
    assert "-able" == r4["suffix"]["str"]
    assert len(r4["parts"]) >= 2, f"Should have at least 2 parts: {r4['parts']}"

    # Prefix + root: "export" (ex- + port)
    r5 = analyze_word("export")
    assert r5["prefix"] is not None, f"Should detect prefix in 'export': {r5}"
    assert r5["prefix"]["str"] == "ex-"
    assert r5["root"] is not None, f"Should detect root 'port' in 'export': {r5}"
    assert r5["root"]["str"] == "port"

    # Suffix only: "careful"
    r6 = analyze_word("careful")
    assert r6["suffix"] is not None, f"Should detect suffix in 'careful': {r6}"
    assert "-ful" == r6["suffix"]["str"]

    # Empty / non-alpha should return no parts
    r7 = analyze_word("")
    assert r7["parts"] == []
    r8 = analyze_word("123")
    assert r8["parts"] == []

    # Short words (< 4 chars) should have no analysis
    r9 = analyze_word("cat")
    assert r9["parts"] == [], f"Short word 'cat' should have no parts: {r9['parts']}"

    # format_analysis returns non-empty for analyzable words
    fmt = format_analysis("unhappy")
    assert len(fmt) > 0, f"format_analysis('unhappy') should be non-empty"
    assert "un-" in fmt, f"Should contain prefix: {fmt}"

    # format_analysis returns empty for non-analyzable words
    fmt2 = format_analysis("cat")
    assert fmt2 == "", f"format_analysis('cat') should be empty: '{fmt2}'"

    # Database sanity checks
    assert len(PREFIXES) >= 40, f"Expected >= 40 prefixes, got {len(PREFIXES)}"
    assert len(SUFFIXES) >= 30, f"Expected >= 30 suffixes, got {len(SUFFIXES)}"
    assert len(ROOTS) >= 80, f"Expected >= 80 roots, got {len(ROOTS)}"

    # "construction" should detect root "struct"
    r10 = analyze_word("construction")
    assert r10["root"] is not None, f"Should detect root in 'construction': {r10}"
    assert r10["root"]["str"] == "struct"

    # "invisible" — in- prefix + vis root
    r11 = analyze_word("invisible")
    assert r11["prefix"] is not None, f"Should detect prefix in 'invisible': {r11}"
    assert r11["root"] is not None, f"Should detect root in 'invisible': {r11}"
    assert "vis" == r11["root"]["str"]

    # "beautiful" — -ful suffix
    r12 = analyze_word("beautiful")
    assert r12["suffix"] is not None, f"Should detect suffix in 'beautiful': {r12}"


test("Word Root Analysis", test_word_root)


# 28. Synonyms & Antonyms (近义词/反义词)
def test_synonyms():
    from synonyms import get_synonyms, get_antonyms, get_related_words, format_related_words, has_data

    # Basic synonym lookup
    syns = get_synonyms("happy")
    assert len(syns) > 0, f"'happy' should have synonyms: {syns}"
    assert "glad" in syns, f"'glad' should be synonym of 'happy': {syns}"
    assert "cheerful" in syns, f"'cheerful' should be synonym of 'happy': {syns}"

    # Basic antonym lookup
    ants = get_antonyms("happy")
    assert len(ants) > 0, f"'happy' should have antonyms: {ants}"
    assert "sad" in ants, f"'sad' should be antonym of 'happy': {ants}"

    # get_related_words returns both
    related = get_related_words("happy")
    assert "synonyms" in related
    assert "antonyms" in related
    assert len(related["synonyms"]) > 0
    assert len(related["antonyms"]) > 0

    # format_related_words
    fmt = format_related_words("happy")
    assert "近义词" in fmt, f"Should contain '近义词': {fmt}"
    assert "反义词" in fmt, f"Should contain '反义词': {fmt}"
    assert "glad" in fmt
    assert "sad" in fmt

    # has_data
    assert has_data("happy") is True
    assert has_data("nonexistent") is False

    # Case insensitive
    assert len(get_synonyms("HAPPY")) > 0
    assert len(get_antonyms("Happy")) > 0

    # Empty / None
    assert get_synonyms("") == []
    assert get_antonyms("") == []
    assert get_synonyms(None) == []

    # Word not in database
    assert get_synonyms("xyznonexistent") == []
    assert get_antonyms("xyznonexistent") == []
    assert format_related_words("xyznonexistent") == ""

    # Verify some verb entries
    syns_accept = get_synonyms("accept")
    assert "receive" in syns_accept, f"'receive' should be synonym of 'accept': {syns_accept}"
    ants_accept = get_antonyms("accept")
    assert "reject" in ants_accept, f"'reject' should be antonym of 'accept': {ants_accept}"

    # Verify some noun entries
    syns_happiness = get_synonyms("happiness")
    assert "joy" in syns_happiness, f"'joy' should be synonym of 'happiness': {syns_happiness}"
    ants_happiness = get_antonyms("happiness")
    assert "sadness" in ants_happiness, f"'sadness' should be antonym of 'happiness': {ants_happiness}"

    # Verify some adverb entries
    syns_quickly = get_synonyms("quickly")
    assert "rapidly" in syns_quickly, f"'rapidly' should be synonym of 'quickly': {syns_quickly}"
    ants_quickly = get_antonyms("quickly")
    assert "slowly" in ants_quickly, f"'slowly' should be antonym of 'quickly': {ants_quickly}"

    # Database should have reasonable coverage
    from synonyms import _SYNONYM_ANTONYM_DB
    assert len(_SYNONYM_ANTONYM_DB) >= 200, f"Expected >= 200 entries, got {len(_SYNONYM_ANTONYM_DB)}"


test("Synonyms & Antonyms", test_synonyms)


# 29. Collocations (常用搭配)
def test_collocations():
    from collocations import get_collocations, format_collocations, has_data

    # Basic collocation lookup
    colls = get_collocations("make")
    assert len(colls) > 0, f"'make' should have collocations: {colls}"
    assert "make a decision" in colls, f"'make a decision' should be collocation of 'make': {colls}"
    assert "make progress" in colls, f"'make progress' should be collocation of 'make': {colls}"

    # Another verb
    colls_take = get_collocations("take")
    assert "take a break" in colls_take
    assert "take care of" in colls_take

    # Noun collocations
    colls_time = get_collocations("time")
    assert "in time" in colls_time
    assert "on time" in colls_time

    # Adjective collocations
    colls_good = get_collocations("good")
    assert "good at" in colls_good

    # format_collocations
    fmt = format_collocations("make")
    assert "常用搭配" in fmt, f"Should contain '常用搭配': {fmt}"
    assert "make a decision" in fmt
    assert "•" in fmt, f"Should contain bullet points: {fmt}"

    # has_data
    assert has_data("make") is True
    assert has_data("take") is True
    assert has_data("nonexistent_xyz") is False

    # Case insensitive
    assert len(get_collocations("MAKE")) > 0
    assert len(get_collocations("Make")) > 0

    # Empty / None
    assert get_collocations("") == []
    assert get_collocations(None) == []
    assert format_collocations("") == ""
    assert format_collocations("nonexistent_xyz") == ""
    assert has_data("") is False
    assert has_data(None) is False

    # Word not in database
    assert get_collocations("xyznonexistent") == []

    # Database should have reasonable coverage
    from collocations import _COLLOCATIONS_DB
    assert len(_COLLOCATIONS_DB) >= 100, f"Expected >= 100 entries, got {len(_COLLOCATIONS_DB)}"

    # Each entry should have at least 3 collocations
    for word, colls in _COLLOCATIONS_DB.items():
        assert len(colls) >= 3, f"'{word}' should have >= 3 collocations, got {len(colls)}"

    # Check some specific adverb entries
    colls_even = get_collocations("even")
    assert "even if" in colls_even

    # Check some specific preposition entries
    colls_despite = get_collocations("despite")
    assert "despite the fact" in colls_despite

    # Return type should be list (copy, not reference)
    colls1 = get_collocations("make")
    colls2 = get_collocations("make")
    assert colls1 is not colls2, "Should return a new list each time"


test("Collocations", test_collocations)


# 30. Auto-start registry management
def test_autostart():
    from src.utils.autostart import (
        is_autostart_enabled, enable_autostart, disable_autostart, set_autostart,
    )
    import sys

    if sys.platform != "win32":
        # On non-Windows, all functions should return False/no-op
        assert is_autostart_enabled() is False
        assert enable_autostart() is False
        assert disable_autostart() is False
        assert set_autostart(True) is False
        return

    # Save current state
    original = is_autostart_enabled()

    # Test enable
    result = enable_autostart()
    assert result is True, "enable_autostart should return True on Windows"
    assert is_autostart_enabled() is True, "should be enabled after enable_autostart"

    # Test disable
    result = disable_autostart()
    assert result is True, "disable_autostart should return True on Windows"
    assert is_autostart_enabled() is False, "should be disabled after disable_autostart"

    # Test set_autostart toggle
    set_autostart(True)
    assert is_autostart_enabled() is True
    set_autostart(False)
    assert is_autostart_enabled() is False

    # Disable again is idempotent
    assert disable_autostart() is True
    assert is_autostart_enabled() is False

    # Restore original state
    if original:
        enable_autostart()


test("Auto-start", test_autostart)


# 31. Context menu registry management
def test_context_menu():
    from src.utils.context_menu import (
        is_installed, install, uninstall, set_enabled,
    )
    import sys

    if sys.platform != "win32":
        # On non-Windows, all functions should return False/no-op
        assert is_installed() is False
        assert install() is False
        assert uninstall() is False
        assert set_enabled(True) is False
        return

    # Save current state
    original = is_installed()

    # Test install
    result = install()
    assert result is True, "install() should return True on Windows"
    assert is_installed() is True, "should be installed after install()"

    # Test uninstall
    result = uninstall()
    assert result is True, "uninstall() should return True on Windows"
    assert is_installed() is False, "should be uninstalled after uninstall()"

    # Test set_enabled toggle
    set_enabled(True)
    assert is_installed() is True
    set_enabled(False)
    assert is_installed() is False

    # Uninstall again is idempotent
    assert uninstall() is True
    assert is_installed() is False

    # Restore original state
    if original:
        install()


test("Context Menu", test_context_menu)


# 32. Config context_menu field
def test_config_context_menu():
    from src.utils.config import load_config, save_config
    cfg = load_config()
    assert hasattr(cfg, 'context_menu')
    assert cfg.context_menu.enabled is False


test("Config Context Menu", test_config_context_menu)


print(f"\nResults: {32 - len(errors)} passed / {len(errors)} failed")
if errors:
    print(f"Failures: {errors}")
    sys.exit(1)
else:
    print("All tests passed!")
