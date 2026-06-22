"""
Quick Translate - 轻量级查词翻译工具
全局快捷键 Shift+Ctrl+M 唤出，Spotlight 风格
"""
import sys
import os
import ctypes
import logging
import time
from pathlib import Path

# 仅支持 Windows
if sys.platform != 'win32':
    print("此程序仅支持 Windows 系统")
    sys.exit(1)

# DPI 感知（必须在 import tkinter 前）
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

PROJECT_DIR = str(Path(__file__).parent.absolute())
sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)


# ── 单实例检测 ──

class SingleInstance:
    """使用 Windows Mutex 确保唯一运行实例"""

    def __init__(self, app_id='QuickTranslateMutex'):
        self._mutex = None
        self._app_id = app_id

    def check(self) -> bool:
        """返回 True 表示已有实例在运行"""
        try:
            self._mutex = ctypes.windll.kernel32.CreateMutexW(None, False, self._app_id)
            return ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
        except Exception:
            return False

    def release(self):
        if self._mutex:
            try:
                ctypes.windll.kernel32.ReleaseMutex(self._mutex)
                ctypes.windll.kernel32.CloseHandle(self._mutex)
            except Exception:
                pass
            self._mutex = None


# ── 日志配置 ──

def setup_logging():
    log_dir = os.path.join(os.path.expanduser("~"), ".quick-translate", "logs")
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger('QuickTranslate')
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    # 文件日志
    log_file = os.path.join(log_dir, f'{time.strftime("%Y%m%d")}.log')
    fh = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s', '%Y-%m-%d %H:%M:%S'))
    logger.addHandler(fh)

    # 控制台日志
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(ch)

    return logger


# ── 主应用 ──

def main():
    # Parse --translate CLI argument (launched from context menu)
    translate_text = None
    if "--translate" in sys.argv:
        idx = sys.argv.index("--translate")
        if idx + 1 < len(sys.argv):
            translate_text = sys.argv[idx + 1].strip()

    # 单实例检测
    instance = SingleInstance()
    if instance.check():
        # If launched with --translate, try to send text to existing instance
        # via a simple file-based IPC (clipboard approach)
        if translate_text:
            import subprocess
            # Copy text to clipboard using Windows clip command
            try:
                proc = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
                proc.communicate(translate_text.encode("utf-16-le"))
            except Exception:
                pass
            print(f"Quick Translate 已在运行，已复制到剪贴板: {translate_text[:50]}")
        else:
            print("Quick Translate 已在运行中")
        sys.exit(0)

    logger = setup_logging()
    logger.info("Quick Translate 启动中...")

    from config import load_config, save_config
    from hotkey import HotkeyListener
    from dictionary import Dictionary
    from translator import AITranslator, MultiAITranslator
    from history import SearchHistory
    from translation_history import TranslationHistory
    from vocabulary import VocabularyBook
    from stats import SearchStats
    from tray import SystemTrayIcon
    from error_handler import ErrorHandler
    from ui import SpotlightUI

    cfg = load_config()

    # 初始化语言
    from src.i18n import set_language, t as _t
    set_language(cfg.get("language", "zh"))

    import tkinter as tk

    # 错误处理器
    error_handler = ErrorHandler()

    # 加载 MDX 原生词典（后台初始化，不阻塞启动）
    from src.core.dict.mdx_dict import MDXDictionary
    import threading
    mdx_path_cfg = cfg["dictionary"].get("mdx_path",
        "data/dict/牛津高阶第10版英汉双解V132/牛津高阶第10版英汉双解V132.mdx")
    if not os.path.isabs(mdx_path_cfg):
        mdx_path_cfg = os.path.join(PROJECT_DIR, mdx_path_cfg)
    mdx_dict = None
    if os.path.exists(mdx_path_cfg):
        mdx_dict = MDXDictionary(mdx_path_cfg)
        def _init_mdx():
            mdx_dict.initialize()
            logger.info(f"MDX 词典就绪: {mdx_dict.word_count:,} 词条")
        threading.Thread(target=_init_mdx, daemon=True).start()
        logger.info("MDX 词典后台初始化中...")
    else:
        logger.warning(f"MDX 词典未找到: {mdx_path_cfg}")

    # 加载 JSON 词典 (MDX 的 fallback)
    dict_path = cfg["dictionary"]["dict_path"]
    if not os.path.isabs(dict_path):
        dict_path = os.path.join(PROJECT_DIR, dict_path)
    dictionary = Dictionary(dict_path, mdx_dict=mdx_dict)
    logger.info(f"词典加载完成: {dictionary.word_count:,} 词条")

    # AI 翻译 — 支持多模型自动切换
    providers = cfg["ai"].get("providers", [])
    if providers:
        ai = MultiAITranslator(
            providers=providers,
            system_prompt=cfg["ai"]["system_prompt"],
            auto_switch=cfg["ai"].get("auto_switch", True),
        )
    else:
        ai = AITranslator(
            api_base=cfg["ai"]["api_base"],
            api_key=cfg["ai"]["api_key"],
            model=cfg["ai"]["model"],
            system_prompt=cfg["ai"]["system_prompt"],
        )
    if ai.is_configured:
        names = ai.get_provider_names() if hasattr(ai, "get_provider_names") else [cfg["ai"]["model"]]
        logger.info(f"AI 翻译: {', '.join(names)}")

    # 查词历史
    history = SearchHistory(max_size=50)

    # AI 翻译历史
    translation_history = TranslationHistory(max_size=200)

    # 生词本
    vocabulary = VocabularyBook(max_size=500)

    # 查词统计
    search_stats = SearchStats()

    # 搜索函数
    def search(query: str):
        results = dictionary.search_fuzzy(query, limit=20)
        if results:
            search_stats.record(query)
        return results

    # 翻译函数（自动保存翻译结果到历史）
    def translate(text, callback, error_callback):
        if not ai.is_configured:
            error_callback(_t("ai_not_configured"))
            return
        if not cfg["ai"]["enabled"]:
            error_callback(_t("ai_disabled"))
            return

        def wrapped_callback(result):
            model_name = ai.current_provider_name if hasattr(ai, "current_provider_name") else ""
            translation_history.add(text, result, model=model_name)
            callback(result)

        ai.translate(text, wrapped_callback, error_callback)

    # 构建 UI
    ui = SpotlightUI(cfg, on_search=search, on_translate=translate,
                     history=history, vocabulary=vocabulary)

    # 热键
    def on_hotkey():
        ui.root.after(0, ui.toggle)

    hk = HotkeyListener(
        shift=cfg["hotkey"]["shift"],
        ctrl=cfg["hotkey"]["ctrl"],
        alt=cfg["hotkey"]["alt"],
        key=cfg["hotkey"]["key"],
        callback=on_hotkey,
    )
    hk.start()

    # 系统托盘
    tray = SystemTrayIcon(
        tooltip="Quick Translate (Shift+Ctrl+M)",
        on_toggle=lambda: ui.root.after(0, ui.toggle),
        on_exit=lambda: ui.root.after(0, ui.root.destroy),
    )
    tray.start()

    # 剪贴板监听（可选功能，默认关闭）
    clipboard_monitor = None
    clip_cfg = cfg.get("clipboard", {})
    if clip_cfg.get("monitor_enabled", False):
        from src.services.clipboard import ClipboardMonitor
        def _on_clipboard_text(text):
            logger.info(f"剪贴板检测: {text[:50]}")
            def _apply():
                ui.show()
                ui.entry.delete(0, tk.END)
                ui.entry.insert(0, text)
                ui._do_search()
            ui.root.after(0, _apply)
        clipboard_monitor = ClipboardMonitor(
            on_text=_on_clipboard_text,
            min_length=clip_cfg.get("min_length", 2),
        )
        clipboard_monitor.start()
        logger.info("剪贴板监听已开启")
    # If launched with --translate, show the UI with the text pre-filled
    if translate_text:
        def _show_translate():
            ui.show()
            ui.entry.delete(0, tk.END)
            ui.entry.insert(0, translate_text)
            ui._do_search()
        # Delay slightly to let UI initialize
        ui.root.after(200, _show_translate)
        logger.info(f"右键翻译: {translate_text[:50]}")

    # 自动更新检测
    try:
        from updater import UpdateChecker
        def _on_update(version, url):
            logger.info(f"发现新版本: v{version} — {url}")
            print(f"[QuickTranslate] 发现新版本 v{version}: {url}")
            try:
                tray.show_notification(
                    _t("new_version_title"),
                    _t("new_version_body", version),
                    timeout_ms=15000,
                )
            except Exception:
                pass  # 通知失败不影响主程序
        update_checker = UpdateChecker(on_update=_on_update)
        update_checker.check_async()
    except Exception:
        pass  # 更新检测失败不影响主程序

    print(f"[QuickTranslate] Ready! Press Shift+Ctrl+M to open.")
    print(f"[QuickTranslate] Dictionary: {dictionary.word_count} words")

    try:
        ui.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"未捕获异常: {e}", exc_info=True)
        # 自动保存崩溃报告
        try:
            from src.utils.crash_report import collect_and_save
            report_path = collect_and_save(context="main_uncaught")
            logger.error(f"Crash report saved to: {report_path}")
        except Exception:
            pass
    finally:
        if clipboard_monitor:
            clipboard_monitor.stop()
        ui._save_position()
        cfg["window_position"] = cfg.get("window_position", {})
        save_config(cfg)
        tray.stop()
        hk.stop()
        instance.release()
        logger.info("Quick Translate 已退出")


if __name__ == "__main__":
    main()
