"""Quick Translate - 轻量级查词翻译工具
全局快捷键 Shift+Ctrl+M 唤出，实时匹配，本地词典 + AI 翻译
"""
import sys
import os

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)

from config import load_config, save_config
from hotkey import HotkeyListener
from dictionary import Dictionary
from translator import AITranslator
from history import SearchHistory
from tray import SystemTrayIcon
from ui import SpotlightUI


def main():
    print("[QuickTranslate] Starting...")
    cfg = load_config()

    # 加载本地词典
    dict_path = cfg["dictionary"]["dict_path"]
    if not os.path.isabs(dict_path):
        dict_path = os.path.join(PROJECT_DIR, dict_path)
    dictionary = Dictionary(dict_path)

    # 初始化 AI 翻译
    ai = AITranslator(
        api_base=cfg["ai"]["api_base"],
        api_key=cfg["ai"]["api_key"],
        model=cfg["ai"]["model"],
        system_prompt=cfg["ai"]["system_prompt"],
    )

    # 初始化查词历史
    history = SearchHistory(max_size=50)

    # 搜索函数（查本地词典 + 历史）
    def search(query: str):
        return dictionary.search_fuzzy(query, limit=20)

    # 翻译函数
    def translate(text, callback, error_callback):
        if not ai.is_configured:
            error_callback("AI 翻译未配置。请在 ~/.quick-translate/config.json 中设置 api_key")
            return
        if not cfg["ai"]["enabled"]:
            error_callback("AI 翻译已禁用")
            return
        ai.translate(text, callback, error_callback)

    # 构建 UI
    ui = SpotlightUI(
        cfg,
        on_search=search,
        on_translate=translate,
        history=history,
    )

    # 热键回调
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
    print(f"[QuickTranslate] Dictionary: {dictionary.word_count} words loaded")
    if ai.is_configured:
        print(f"[QuickTranslate] AI: {cfg['ai']['model']} @ {cfg['ai']['api_base']}")

    try:
        ui.run()
    except KeyboardInterrupt:
        pass
    finally:
        # 退出前保存状态
        ui._save_position()
        cfg["window_position"] = cfg.get("window_position", {})
        save_config(cfg)
        tray.stop()
        hk.stop()
        print("[QuickTranslate] Bye!")


if __name__ == "__main__":
    main()
