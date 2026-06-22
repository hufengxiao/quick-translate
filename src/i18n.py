"""
国际化 (i18n) 模块 — 支持中文/英文界面切换
"""
_current_lang = "zh"

# All UI translations keyed by string identifier
_TRANSLATIONS: dict = {
    "zh": {
        # ── 通用 ──
        "app_name": "Quick Translate",
        "cancel": "取消",
        "save": "保存",
        "reset_defaults": "恢复默认",
        "error": "错误",
        "copied_to_clipboard": "已复制到剪贴板 ✓",
        "settings_saved": "设置已保存 ✓",

        # ── 搜索/列表 ──
        "search_placeholder": "输入单词开始查询…",
        "search_error": "搜索出错",
        "no_local_results": "  \U0001f916 本地无结果，按 Enter AI 翻译",
        "recent_searches": "最近查词",
        "recent_search_hint": "输入新的单词开始查询，或从历史中选择",
        "no_definition": "无释义",
        "no_local_definition": "未找到本地释义",
        "ai_press_enter": "按 Enter 使用 AI 翻译 \"{}\"",
        # ── AI 翻译 ──
        "ai_translating": "\U0001f916 AI 翻译中\u2026",
        "ai_translating_detail": "正在翻译 \"{}\"，请稍候\u2026",
        "ai_result": "\U0001f916 AI 翻译结果",
        "translation_failed": "翻译失败",
        "error_detail": "错误: {}",
        "ai_not_configured": "AI 翻译未配置",
        "ai_disabled": "AI 翻译已禁用",
        "ai_no_providers": "没有可用的 AI 模型",
        "ai_all_failed": "所有 AI 模型都失败:\n{}",
        # ── 返回按钮 ──
        "back_to_list": "\u2190 返回列表",

        # ── 收藏/星标 ──
        "favorited": "已收藏 \"{}\" \u2605",
        "unfavorited": "已取消收藏 \"{}\"",
        "starred": "已星标 \"{}\" \u25c6",
        "unstarred": "已取消星标 \"{}\"",

        # ── 字体大小 ──
        "font_size_toast": "字体大小 {} ({})",

        # ── 新手引导 ──
        "guide_hotkey": "Shift+Ctrl+M 唤出窗口",
        "guide_search": "输入英文查词，\u2191\u2193 选择",
        "guide_enter_esc": "Enter 查看详情 | Esc 返回",
        "guide_tab_copy": "Tab AI翻译 | 点击释义复制",

        # ── 设置面板 ──
        "settings": "\u2699 设置",
        "appearance": "外观",
        "theme": "主题",
        "theme_system": "跟随系统",
        "theme_dark": "深色",
        "theme_light": "浅色",
        "theme_high_contrast": "高对比",
        "opacity": "透明度",
        "font_size": "字体大小",
        "animation_speed": "动画速度 (倍率)",
        "hotkey": "快捷键",
        "trigger_key": "触发键",
        "hotkey_restart_hint": "修改后需重启程序生效",
        "ai_translation": "AI 翻译",
        "enable_ai": "启用 AI 翻译",
        "api_base": "API 地址",
        "api_key": "API 密钥",
        "model": "模型",
        "clipboard": "剪贴板",
        "clipboard_monitor": "监听剪贴板自动翻译",
        "min_chars": "最小字符数",
        "startup": "启动",
        "autostart": "开机自启动",
        "autostart_hint": "开启后 Windows 启动时自动运行",
        "context_menu": "右键菜单",
        "context_menu_enable": "添加右键菜单翻译",
        "context_menu_hint": "右键文件/文件夹时显示\"用 Quick Translate 翻译\"",
        "language": "语言",

        # ── 托盘 ──
        "tray_show_hide": "显示/隐藏",
        "tray_exit": "退出",

        # ── 启动/更新 ──
        "only_windows": "此程序仅支持 Windows 系统",
        "already_running": "Quick Translate 已在运行中",
        "clipboard_copied": "Quick Translate 已在运行，已复制到剪贴板: {}",
        "starting": "Quick Translate 启动中...",
        "new_version_title": "Quick Translate \u2014 发现新版本",
        "new_version_body": "新版本 v{} 已发布！点击查看详情",
        "mdx_ready": "MDX 词典就绪: {} 词条",
        "mdx_loading": "MDX 词典后台初始化中...",
        "mdx_not_found": "MDX 词典未找到: {}",
        "dict_loaded": "词典加载完成: {} 词条",
        "ai_providers": "AI 翻译: {}",
        "clipboard_monitor_on": "剪贴板监听已开启",
        "clipboard_detected": "剪贴板检测: {}",
        "ready": "[QuickTranslate] Ready! Press Shift+Ctrl+M to open.",
        "ready_dict": "[QuickTranslate] Dictionary: {} words",
        "exited": "Quick Translate 已退出",
    },
    "en": {
        # ── General ──
        "app_name": "Quick Translate",
        "cancel": "Cancel",
        "save": "Save",
        "reset_defaults": "Reset Defaults",
        "error": "Error",
        "copied_to_clipboard": "Copied to clipboard \u2713",
        "settings_saved": "Settings saved \u2713",

        # ── Search / List ──
        "search_placeholder": "Type a word to search\u2026",
        "search_error": "Search error",
        "no_local_results": "  \U0001f916 No local results, press Enter for AI translation",
        "recent_searches": "Recent Searches",
        "recent_search_hint": "Type a new word or select from history",
        "no_definition": "No definition",
        "no_local_definition": "No local definition",
        "ai_press_enter": "Press Enter for AI translation \"{}\"",
        # ── AI Translation ──
        "ai_translating": "\U0001f916 AI Translating\u2026",
        "ai_translating_detail": "Translating \"{}\", please wait\u2026",
        "ai_result": "\U0001f916 AI Translation Result",
        "translation_failed": "Translation Failed",
        "error_detail": "Error: {}",
        "ai_not_configured": "AI translation not configured",
        "ai_disabled": "AI translation disabled",
        "ai_no_providers": "No AI models available",
        "ai_all_failed": "All AI models failed:\n{}",
        # ── Back button ──
        "back_to_list": "\u2190 Back to List",

        # ── Favorite / Star ──
        "favorited": "Favorited \"{}\" \u2605",
        "unfavorited": "Removed \"{}\" from favorites",
        "starred": "Starred \"{}\" \u25c6",
        "unstarred": "Un-starred \"{}\"",

        # ── Font size ──
        "font_size_toast": "Font size {} ({})",

        # ── Guide ──
        "guide_hotkey": "Shift+Ctrl+M to open window",
        "guide_search": "Type to search, \u2191\u2193 to select",
        "guide_enter_esc": "Enter for details | Esc to go back",
        "guide_tab_copy": "Tab for AI | Click definition to copy",

        # ── Settings Panel ──
        "settings": "\u2699 Settings",
        "appearance": "Appearance",
        "theme": "Theme",
        "theme_system": "System",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "theme_high_contrast": "High Contrast",
        "opacity": "Opacity",
        "font_size": "Font Size",
        "animation_speed": "Animation Speed (multiplier)",
        "hotkey": "Hotkey",
        "trigger_key": "Trigger Key",
        "hotkey_restart_hint": "Restart required after changes",
        "ai_translation": "AI Translation",
        "enable_ai": "Enable AI Translation",
        "api_base": "API Base URL",
        "api_key": "API Key",
        "model": "Model",
        "clipboard": "Clipboard",
        "clipboard_monitor": "Auto-translate clipboard content",
        "min_chars": "Minimum Characters",
        "startup": "Startup",
        "autostart": "Launch on Startup",
        "autostart_hint": "Auto-run when Windows starts",
        "context_menu": "Context Menu",
        "context_menu_enable": "Add context menu translation",
        "context_menu_hint": "Show \"Translate with Quick Translate\" in right-click menu",
        "language": "Language",

        # ── Tray ──
        "tray_show_hide": "Show/Hide",
        "tray_exit": "Exit",

        # ── Startup / Update ──
        "only_windows": "This program only supports Windows",
        "already_running": "Quick Translate is already running",
        "clipboard_copied": "Quick Translate already running, copied to clipboard: {}",
        "starting": "Quick Translate starting...",
        "new_version_title": "Quick Translate \u2014 New Version Available",
        "new_version_body": "Version v{} has been released! Click for details",
        "mdx_ready": "MDX dictionary ready: {} entries",
        "mdx_loading": "MDX dictionary loading in background...",
        "mdx_not_found": "MDX dictionary not found: {}",
        "dict_loaded": "Dictionary loaded: {} entries",
        "ai_providers": "AI Translation: {}",
        "clipboard_monitor_on": "Clipboard monitor enabled",
        "clipboard_detected": "Clipboard detected: {}",
        "ready": "[QuickTranslate] Ready! Press Shift+Ctrl+M to open.",
        "ready_dict": "[QuickTranslate] Dictionary: {} words",
        "exited": "Quick Translate exited",
    },
}


def set_language(lang: str):
    """Set the current UI language. Accepts 'zh' or 'en'."""
    global _current_lang
    if lang in _TRANSLATIONS:
        _current_lang = lang


def get_language() -> str:
    """Return the current language code."""
    return _current_lang


def t(key: str, *args) -> str:
    """Translate a key to the current language.

    Supports positional format args, e.g. t("error_detail", "timeout")
    returns "错误: timeout" in Chinese or "Error: timeout" in English.
    """
    lang_map = _TRANSLATIONS.get(_current_lang, _TRANSLATIONS["zh"])
    text = lang_map.get(key)
    if text is None:
        # Fallback to Chinese
        text = _TRANSLATIONS["zh"].get(key, key)
    if args:
        try:
            return text.format(*args)
        except (IndexError, KeyError):
            return text
    return text
