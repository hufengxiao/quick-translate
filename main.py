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
    # 单实例检测
    instance = SingleInstance()
    if instance.check():
        print("Quick Translate 已在运行中")
        sys.exit(0)

    logger = setup_logging()
    logger.info("Quick Translate 启动中...")

    from config import load_config, save_config
    from hotkey import HotkeyListener
    from dictionary import Dictionary
    from translator import AITranslator
    from history import SearchHistory
    from tray import SystemTrayIcon
    from error_handler import ErrorHandler
    from ui import SpotlightUI

    cfg = load_config()

    # 错误处理器
    error_handler = ErrorHandler()

    # 加载 MDX 原生词典（后台初始化，不阻塞启动）
    from src.core.dict.mdx_dict import MDXDictionary
    import threading
    mdx_path = os.path.join(PROJECT_DIR, "data", "dict",
                            "牛津高阶第10版英汉双解V132", "牛津高阶第10版英汉双解V132.mdx")
    mdx_dict = None
    if os.path.exists(mdx_path):
        mdx_dict = MDXDictionary(mdx_path)
        def _init_mdx():
            mdx_dict.initialize()
            logger.info(f"MDX 词典就绪: {mdx_dict.word_count:,} 词条")
        threading.Thread(target=_init_mdx, daemon=True).start()
        logger.info("MDX 词典后台初始化中...")

    # 加载 JSON 词典 (MDX 的 fallback)
    dict_path = cfg["dictionary"]["dict_path"]
    if not os.path.isabs(dict_path):
        dict_path = os.path.join(PROJECT_DIR, dict_path)
    dictionary = Dictionary(dict_path, mdx_dict=mdx_dict)
    logger.info(f"词典加载完成: {dictionary.word_count:,} 词条")

    # AI 翻译
    ai = AITranslator(
        api_base=cfg["ai"]["api_base"],
        api_key=cfg["ai"]["api_key"],
        model=cfg["ai"]["model"],
        system_prompt=cfg["ai"]["system_prompt"],
    )
    if ai.is_configured:
        logger.info(f"AI 翻译: {cfg['ai']['model']}")

    # 查词历史
    history = SearchHistory(max_size=50)

    # 搜索函数
    def search(query: str):
        return dictionary.search_fuzzy(query, limit=20)

    # 翻译函数
    def translate(text, callback, error_callback):
        if not ai.is_configured:
            error_callback("AI 翻译未配置")
            return
        if not cfg["ai"]["enabled"]:
            error_callback("AI 翻译已禁用")
            return
        ai.translate(text, callback, error_callback)

    # 构建 UI
    ui = SpotlightUI(cfg, on_search=search, on_translate=translate, history=history)

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

    print(f"[QuickTranslate] Ready! Press Shift+Ctrl+M to open.")
    print(f"[QuickTranslate] Dictionary: {dictionary.word_count} words")

    try:
        ui.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"未捕获异常: {e}", exc_info=True)
    finally:
        ui._save_position()
        cfg["window_position"] = cfg.get("window_position", {})
        save_config(cfg)
        tray.stop()
        hk.stop()
        instance.release()
        logger.info("Quick Translate 已退出")


if __name__ == "__main__":
    main()
