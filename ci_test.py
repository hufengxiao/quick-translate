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


print("Running tests...")
test("Config", test_config)
test("Errors", test_errors)
test("ExactIndex", test_exact)
test("TrieIndex", test_trie)
test("BK-Tree", test_bktree)
test("LRU Cache", test_lru)
test("Dictionary", test_dictionary)
test("Theme", test_theme)
test("Translator", test_translator)
test("No TTS", test_no_tts)


# 11. Startup benchmark
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


# 12. Query performance
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
    assert t2 < 1.0, f"Prefix too slow: {t2:.2f}ms > 1ms"


test("Query Perf", test_query_perf)

print(f"\nResults: {10 - len(errors)} passed / {len(errors)} failed")
if errors:
    print(f"Failures: {errors}")
    sys.exit(1)
else:
    print("All tests passed!")
