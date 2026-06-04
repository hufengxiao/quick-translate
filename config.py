"""配置管理模块"""
import json
import os

APP_NAME = "QuickTranslate"
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".quick-translate")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "hotkey": {"shift": True, "ctrl": True, "alt": False, "key": "m"},
    "ui": {
        "width": 340,
        "height": 480,
        "opacity": 0.95,
        "font_size": 13,
        "bg_color": "#1e1e2e",
        "fg_color": "#cdd6f4",
        "accent_color": "#89b4fa",
        "entry_bg": "#313244",
        "list_bg": "#181825",
        "highlight_bg": "#45475a",
    },
    "ai": {
        "enabled": True,
        "api_base": "https://token-plan-cn.xiaomimimo.com/v1",
        "api_key": "tp-cr6615u5dv567yf4rrh1jti1cffpjuqrzvrqffru364ori7d",
        "model": "mimo-v2.5",
        "system_prompt": (
            "You are a professional English-Chinese dictionary assistant. "
            "When the user inputs a single English word, provide a detailed dictionary entry in this format:\n"
            "音标 (phonetic)\n"
            "词性 (part of speech)\n"
            "中文释义 — list ALL common meanings, numbered\n"
            "常用搭配 — collocations and phrases\n"
            "例句 — 2-3 example sentences with bilingual translation\n"
            "近义词 — synonyms\n"
            "\n"
            "When the user inputs a Chinese word or phrase, provide:\n"
            "英文翻译\n"
            "用法说明\n"
            "2-3 例句\n"
            "\n"
            "When the user inputs a sentence, translate it fluently and explain key grammar points.\n"
            "Always be thorough and helpful. Use Chinese for explanations. "
            "Format neatly with line breaks. Do not be overly brief."
        ),
    },
    "dictionary": {
        "dict_path": "data/dict/ecdict.json",
    },
}


def load_config() -> dict:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    user_cfg = json.loads(content)
                    cfg = _deep_merge(DEFAULT_CONFIG.copy(), user_cfg)
                    return cfg
        except Exception:
            pass
    # 首次运行：写入默认配置
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def _deep_merge(base: dict, override: dict) -> dict:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            base[k] = _deep_merge(base[k], v)
        else:
            base[k] = v
    return base
