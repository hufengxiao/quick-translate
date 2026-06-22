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

print(f"\nResults: {18 - len(errors)} passed / {len(errors)} failed")
if errors:
    print(f"Failures: {errors}")
    sys.exit(1)
else:
    print("All tests passed!")
