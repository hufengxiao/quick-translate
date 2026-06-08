"""Quick Translate — Apple-grade Windows dictionary tool.

Phase 2: clipboard monitor, TTS pronunciation, multi-dict sources.
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
from src.ui.spotlight import SpotlightUI
from src.services.clipboard import ClipboardMonitor
from src.services.tts import TTSService
from src.services.dict_sources.sources import LocalDictSource, YoudaoDictSource

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
    logger.info("Quick Translate v1.2.0 starting...")

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

    # ── 4. Multi-dict sources ──
    local_source = LocalDictSource(dictionary)
    youdao_source = YoudaoDictSource()

    # ── 5. TTS ──
    tts = TTSService()
    if tts.is_available:
        logger.info("TTS available — pronunciation enabled")
    else:
        logger.info("TTS not available (install pywin32 for pronunciation)")

    # ── 6. History ──
    history = SearchHistory(max_size=50)

    # ── 7. Search function (local first, youdao fallback) ──
    def search(query: str):
        results = dictionary.search(query, limit=20)
        # If no local results and query looks like a single word, try youdao
        if not results and len(query.split()) == 1 and len(query) < 30:
            youdao_result = youdao_source.lookup(query)
            if youdao_result:
                results = [youdao_result]
        return results

    # ── 8. Translate function ──
    def translate(text, callback, error_callback):
        if not ai.is_configured:
            error_callback("AI 翻译未配置。请在 ~/.quick-translate/config.json 中设置 api_key")
            return
        if not cfg.ai.enabled:
            error_callback("AI 翻译已禁用")
            return
        ai.translate(text, callback, error_callback)

    # ── 9. Pronunciation function ──
    def pronounce(word: str):
        if tts.is_available:
            tts.speak(word)

    # ── 10. Build UI ──
    ui = SpotlightUI(
        cfg,
        on_search=search,
        on_translate=translate,
        history=history,
        on_pronounce=pronounce,
    )

    # ── 11. Clipboard monitor ──
    def on_clipboard_text(text: str):
        """Called when clipboard has new translatable text."""
        # Show the window and insert text into search
        ui.root.after(0, lambda: ui.show_and_search(text))

    clipboard = ClipboardMonitor(
        on_text=on_clipboard_text,
        min_length=cfg.clipboard.min_length,
        auto_translate=cfg.clipboard.monitor_enabled,
    )
    clipboard.start()

    # ── 12. Hotkey ──
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

    # ── 13. System Tray ──
    _mods = []
    if cfg.hotkey.shift: _mods.append("Shift")
    if cfg.hotkey.ctrl: _mods.append("Ctrl")
    if cfg.hotkey.alt: _mods.append("Alt")
    if cfg.hotkey.win: _mods.append("Win")
    _mods.append(cfg.hotkey.key.upper())
    tray = SystemTrayIcon(
        tooltip=f"Quick Translate ({'+'.join(_mods)})",
        on_toggle=lambda: ui.root.after(0, ui.toggle),
        on_exit=lambda: ui.root.after(0, ui.root.destroy),
    )
    tray.start()

    # ── 14. Ready ──
    t_ready = time.perf_counter()
    startup_ms = (t_ready - t_start) * 1000
    features = ["dict", "ai"]
    if tts.is_available:
        features.append("tts")
    if cfg.clipboard.monitor_enabled:
        features.append("clipboard")
    logger.info("Ready! Startup: {:.0f}ms | Features: {} | Dictionary: {} words",
                startup_ms, "+".join(features), dictionary.word_count)
    print(f"[QuickTranslate] Ready in {startup_ms:.0f}ms! Press Shift+Ctrl+M to open.")
    print(f"[QuickTranslate] Features: {', '.join(features)} | {dictionary.word_count} words")

    try:
        ui.run()
    except KeyboardInterrupt:
        pass
    finally:
        ui._save_position()
        save_config(cfg)
        clipboard.stop()
        tray.stop()
        hk.stop()
        logger.info("Shutdown complete")
        print("[QuickTranslate] Bye!")


if __name__ == "__main__":
    main()
