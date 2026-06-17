#!/usr/bin/env python3
"""Quick Translate 性能基准测试"""
import sys
import os
import time
import timeit

sys.path.insert(0, ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from src.utils.logging import setup_logging
setup_logging("WARNING", False)


def bench(name, fn, number=100):
    """运行基准测试并返回结果"""
    total = timeit.timeit(fn, number=number)
    avg = total / number * 1000
    return name, avg, total


def main():
    print("=" * 50)
    print("  Quick Translate 性能基准测试")
    print("=" * 50)
    print()

    results = []

    # 1. JSON 词典加载
    from dictionary import Dictionary
    t0 = time.perf_counter()
    d = Dictionary("data/dict/ecdict.json")
    elapsed = (time.perf_counter() - t0) * 1000
    results.append(("JSON 词典加载", elapsed, elapsed / 1000))
    print(f"  JSON 词典加载: {elapsed:.0f}ms ({d.word_count:,} 词条)")

    # 2. JSON 前缀搜索
    name, avg, total = bench("JSON 前缀搜索", lambda: d.search_prefix("trans", 10), 1000)
    results.append((name, avg, total))
    print(f"  {name}: {avg:.3f}ms/query")

    # 3. JSON 模糊搜索
    name, avg, total = bench("JSON 模糊搜索", lambda: d.search_fuzzy("hello", 10), 1000)
    results.append((name, avg, total))
    print(f"  {name}: {avg:.3f}ms/query")

    # 4. MDX SQLite 加载
    from src.core.dict.mdx_dict import MDXDictionary
    mdx_path = "data/dict/牛津高阶第10版英汉双解V132/牛津高阶第10版英汉双解V132.mdx"
    if os.path.exists(mdx_path):
        t0 = time.perf_counter()
        mdx = MDXDictionary(mdx_path)
        mdx.initialize()
        elapsed = (time.perf_counter() - t0) * 1000
        results.append(("MDX SQLite 加载", elapsed, elapsed / 1000))
        print(f"  MDX SQLite 加载: {elapsed:.0f}ms ({mdx.word_count:,} 词条)")

        # 5. MDX 精确查询
        name, avg, total = bench("MDX 精确查询", lambda: mdx.lookup("hello"), 100)
        results.append((name, avg, total))
        print(f"  {name}: {avg:.3f}ms/query")

        # 6. MDX 前缀搜索
        name, avg, total = bench("MDX 前缀搜索", lambda: mdx.search_prefix("trans", 10), 100)
        results.append((name, avg, total))
        print(f"  {name}: {avg:.3f}ms/query")

        # 7. MDX HTML→文本转换
        entry = mdx.lookup("hello")
        if entry:
            name, avg, total = bench("MDX HTML→文本", lambda: MDXDictionary.html_to_text(entry["html"]), 100)
            results.append((name, avg, total))
            print(f"  {name}: {avg:.3f}ms/query")

    # 8. 内存使用
    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem_mb = process.memory_info().rss / 1024 / 1024
        results.append(("内存使用", mem_mb, 0))
        print(f"  内存使用: {mem_mb:.1f}MB")
    except ImportError:
        print("  内存使用: (安装 psutil 以查看)")

    # 9. 启动时间
    print()
    t0 = time.perf_counter()
    import subprocess
    r = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0,'.');"
         "from dictionary import Dictionary;"
         "d = Dictionary('data/dict/ecdict.json');"
         "print(d.word_count)"],
        capture_output=True, text=True, timeout=10, cwd=".",
    )
    startup_ms = (time.perf_counter() - t0) * 1000
    print(f"  冷启动: {startup_ms:.0f}ms")

    # 汇总
    print()
    print("=" * 50)
    print(f"  测试完成")
    print("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())
