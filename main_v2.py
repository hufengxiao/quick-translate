"""Quick Translate — Apple-grade Windows dictionary tool.

Phase 1 rewrite: modular architecture, indexed dictionary,
LRU cache, lazy loading, Apple HIG UI, smooth animations.
"""
import sys
import os
import time

# Ensure project root is on path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)

from src.utils.config import load_config, save_config
from src.utils.logging import setup_logging, logger
from src.core.dict.dictionary import Dictionary
from src.core.lazy.loader import LazyDictLoader
from src.ui.spotlight import SpotlightUI

# Keep original modules for features not yet migrated
from hotkey import HotkeyListener
from translator import AITranslator
from history import SearchHistory
from tray import SystemTrayIcon


def main():
    t_start = time.perf_counter()

    # ── 1. Load config ──
    cfg = load_config()
    setup_logging(
        level=cfg.logging.level,
        file_enabled=cfg.logging.file_enabled,
        max_size_mb=cfg.logging.max_size_mb,
    )
    logger.info("Quick Translate v1.1.0 starting...")

    # ── 2. Load dictionary (2-phase: preload → background) ──
    dict_path = cfg.dictionary.dict_path
    if not os.path.isabs(dict_path):
        dict_path = os.path.join(PROJECT_DIR, dict_path)

    dictionary = Dictionary(
        dict_path=dict_path,
        preload_count=cfg.dictionary.preload_count,
        cache_size=cfg.dictionary.cache_size,
    )

    def on_dict_fully_loaded():
        logger.info("Background dictionary load complete — {} words, cache hit rate: {}",
                     dictionary.word_count, dictionary.cache_stats.get("hit_rate", "N/A"))

    dictionary.load(on_background_complete=on_dict_fully_loaded)

    # ── 3. AI Translator ──
    ai = AITranslator(
        api_base=cfg.ai.api_base,
        api_key=cfg.ai.api_key,
        model=cfg.ai.model,
        system_prompt=cfg.ai.system_prompt,
    )

    # ── 4. History ──
    history = SearchHistory(max_size=50)

    # ── 5. Search function ──
    def search(query: str):
        return dictionary.search(query, limit=20)

    # ── 6. Translate function ──
    def translate(text, callback, error_callback):
        if not ai.is_configured:
            error_callback("AI 翻译未配置。请在 ~/.quick-translate/config.json 中设置 api_key")
            return
        if not cfg.ai.enabled:
            error_callback("AI 翻译已禁用")
            return
        ai.translate(text, callback, error_callback)

    # ── 7. Build UI ──
    ui = SpotlightUI(
        cfg,
        on_search=search,
        on_translate=translate,
        history=history,
    )

    # ── 8. Hotkey ──
    def on_hotkey():
        ui.root.after(0, ui.toggle)

    hk = HotkeyListener(
        shift=cfg.hotkey.shift,
        ctrl=cfg.hotkey.ctrl,
        alt=cfg.hotkey.alt,
        key=cfg.hotkey.key,
        callback=on_hotkey,
    )
    hk.start()

    # ── 9. System Tray ──
    tray = SystemTrayIcon(
        tooltip=f"Quick Translate (Shift+Ctrl+M)",
        on_toggle=lambda: ui.root.after(0, ui.toggle),
        on_exit=lambda: ui.root.after(0, ui.root.destroy),
    )
    tray.start()

    # ── 10. Ready ──
    t_ready = time.perf_counter()
    startup_ms = (t_ready - t_start) * 1000
    logger.info("Ready! Startup: {:.0f}ms | Dictionary: {} words | AI: {} @ {}",
                startup_ms, dictionary.word_count,
                cfg.ai.model if ai.is_configured else "not configured",
                cfg.ai.api_base if ai.is_configured else "N/A")
    print(f"[QuickTranslate] Ready in {startup_ms:.0f}ms! Press Shift+Ctrl+M to open.")
    print(f"[QuickTranslate] Dictionary: {dictionary.word_count} words loaded")

    try:
        ui.run()
    except KeyboardInterrupt:
        pass
    finally:
        ui._save_position()
        save_config(cfg)
        tray.stop()
        hk.stop()
        logger.info("Shutdown complete")
        print("[QuickTranslate] Bye!")


if __name__ == "__main__":
    main()
