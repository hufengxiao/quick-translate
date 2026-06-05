"""Configuration management with validation and deep merge."""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

from .errors import ConfigError

APP_NAME = "QuickTranslate"
CONFIG_DIR = Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / ".quick-translate"
CONFIG_FILE = CONFIG_DIR / "config.json"


# ── Dataclass-based config (no pydantic dependency for speed) ──

@dataclass
class HotkeyConfig:
    shift: bool = True
    ctrl: bool = True
    alt: bool = False
    win: bool = False
    key: str = "m"


@dataclass
class UIConfig:
    width: int = 360
    height: int = 520
    opacity: float = 0.96
    font_size: int = 13
    # Apple HIG dark palette
    bg_color: str = "#1C1C1E"
    fg_color: str = "#F5F5F7"
    secondary_fg: str = "#98989D"
    accent_color: str = "#0A84FF"
    entry_bg: str = "#2C2C2E"
    list_bg: str = "#1C1C1E"
    highlight_bg: str = "#3A3A3C"
    separator_color: str = "#38383A"
    # Apple-style extras
    corner_radius: int = 12
    animations_enabled: bool = True
    shadow_enabled: bool = True


@dataclass
class AIConfig:
    enabled: bool = True
    api_base: str = "https://token-plan-cn.xiaomimimo.com/v1"
    api_key: str = "tp-cr6615u5dv567yf4rrh1jti1cffpjuqrzvrqffru364ori7d"
    model: str = "mimo-v2.5"
    system_prompt: str = (
        "You are a professional English-Chinese dictionary assistant. "
        "When the user inputs a single English word, provide a detailed dictionary entry:\n"
        "音标 (phonetic)\n词性 (part of speech)\n"
        "中文释义 — list ALL common meanings, numbered\n"
        "常用搭配 — collocations and phrases\n"
        "例句 — 2-3 example sentences with bilingual translation\n"
        "近义词 — synonyms\n\n"
        "When the user inputs a Chinese word or phrase, provide:\n"
        "英文翻译\n用法说明\n2-3 例句\n\n"
        "When the user inputs a sentence, translate it fluently and explain key grammar points.\n"
        "Always be thorough and helpful. Use Chinese for explanations."
    )


@dataclass
class DictionaryConfig:
    dict_path: str = "data/dict/ecdict.json"
    preload_count: int = 10000
    cache_size: int = 500


@dataclass
class ClipboardConfig:
    monitor_enabled: bool = False
    min_length: int = 2
    auto_translate: bool = False


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file_enabled: bool = True
    max_size_mb: int = 10


@dataclass
class AppConfig:
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    dictionary: DictionaryConfig = field(default_factory=DictionaryConfig)
    clipboard: ClipboardConfig = field(default_factory=ClipboardConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    window_position: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def validate(self) -> list[str]:
        """Return list of validation warnings (empty = all good)."""
        warnings: list[str] = []
        if not (0.1 <= self.ui.opacity <= 1.0):
            warnings.append(f"ui.opacity={self.ui.opacity} out of range [0.1, 1.0], clamping")
            self.ui.opacity = max(0.1, min(1.0, self.ui.opacity))
        if self.ui.font_size < 8 or self.ui.font_size > 24:
            warnings.append(f"ui.font_size={self.ui.font_size} unusual, expected 8-24")
        if self.dictionary.preload_count < 100:
            warnings.append("dictionary.preload_count < 100, search quality may be poor")
        if self.ai.enabled and not self.ai.api_key:
            warnings.append("ai.enabled=true but api_key is empty")
        return warnings


def _deep_merge(base: dict, override: dict) -> dict:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            base[k] = _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def _dict_to_config(d: dict) -> AppConfig:
    """Convert a raw dict to an AppConfig, ignoring unknown keys."""
    cfg = AppConfig()
    if "hotkey" in d:
        for k, v in d["hotkey"].items():
            if hasattr(cfg.hotkey, k):
                setattr(cfg.hotkey, k, v)
    if "ui" in d:
        for k, v in d["ui"].items():
            if hasattr(cfg.ui, k):
                setattr(cfg.ui, k, v)
    if "ai" in d:
        for k, v in d["ai"].items():
            if hasattr(cfg.ai, k):
                setattr(cfg.ai, k, v)
    if "dictionary" in d:
        for k, v in d["dictionary"].items():
            if hasattr(cfg.dictionary, k):
                setattr(cfg.dictionary, k, v)
    if "clipboard" in d:
        for k, v in d["clipboard"].items():
            if hasattr(cfg.clipboard, k):
                setattr(cfg.clipboard, k, v)
    if "logging" in d:
        for k, v in d["logging"].items():
            if hasattr(cfg.logging, k):
                setattr(cfg.logging, k, v)
    if "window_position" in d:
        cfg.window_position = d["window_position"]
    return cfg


def load_config() -> AppConfig:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            raw = CONFIG_FILE.read_text(encoding="utf-8").strip()
            if raw:
                data = json.loads(raw)
                cfg = _dict_to_config(data)
                warnings = cfg.validate()
                for w in warnings:
                    print(f"[Config] Warning: {w}")
                return cfg
        except Exception as e:
            print(f"[Config] Failed to parse config: {e}, using defaults")
    # First run — write defaults
    cfg = AppConfig()
    save_config(cfg)
    return cfg


def save_config(cfg: AppConfig) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(cfg.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
