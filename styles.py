"""
Quick Translate 设计系统
色彩、字体、间距、动画等设计 Token
遵循 Apple HIG 设计语言
"""
from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass(frozen=True)
class ColorPalette:
    """色彩调色板"""
    # 背景
    bg_primary: str
    bg_secondary: str
    bg_tertiary: str
    bg_elevated: str
    bg_glass: str

    # 文字
    text_primary: str
    text_secondary: str
    text_tertiary: str
    text_placeholder: str

    # 边框
    border_subtle: str
    border_default: str
    border_focus: str

    # 品牌色
    accent_primary: str
    accent_secondary: str

    # 语义色
    success: str
    warning: str
    error: str
    info: str


@dataclass(frozen=True)
class FontConfig:
    """字体配置"""
    family: str
    fallback: str
    mono: str
    sizes: Dict[str, int] = field(default_factory=lambda: {
        'search_input': 16,
        'result_title': 13,
        'result_body': 12,
        'result_secondary': 11,
        'label': 10,
        'status': 9,
        'shortcut': 9,
    })


@dataclass(frozen=True)
class Spacing:
    """间距系统（4pt 网格）"""
    space_0: int = 0
    space_1: int = 4
    space_2: int = 8
    space_3: int = 12
    space_4: int = 16
    space_5: int = 20
    space_6: int = 24
    space_8: int = 32


@dataclass(frozen=True)
class Radius:
    """圆角系统"""
    none: int = 0
    sm: int = 6
    md: int = 10
    lg: int = 14
    xl: int = 20
    full: int = 9999


@dataclass(frozen=True)
class Animation:
    """动画参数（毫秒）"""
    duration_fast: int = 80
    duration_normal: int = 150
    duration_slow: int = 250
    frames_fast: int = 8
    frames_normal: int = 15
    frames_slow: int = 25


@dataclass(frozen=True)
class ComponentSizes:
    """组件尺寸"""
    window_width: int = 400
    window_height: int = 500
    search_height: int = 48
    result_item_height: int = 44
    icon_size: int = 16
    status_bar_height: int = 28


# ============ 暗色主题 ============

DARK_PALETTE = ColorPalette(
    bg_primary='#1e1e2e',
    bg_secondary='#282840',
    bg_tertiary='#313244',
    bg_elevated='#45475a',
    bg_glass='rgba(30, 30, 46, 0.92)',

    text_primary='#cdd6f4',
    text_secondary='#a6adc8',
    text_tertiary='#6c7086',
    text_placeholder='#45475a',

    border_subtle='#313244',
    border_default='#45475a',
    border_focus='#89b4fa',

    accent_primary='#89b4fa',
    accent_secondary='#74c7ec',

    success='#a6e3a1',
    warning='#f9e2af',
    error='#f38ba8',
    info='#89dceb',
)

# ============ 亮色主题 ============

LIGHT_PALETTE = ColorPalette(
    bg_primary='#ffffff',
    bg_secondary='#f5f5f7',
    bg_tertiary='#e8e8ed',
    bg_elevated='#ffffff',
    bg_glass='rgba(255, 255, 255, 0.92)',

    text_primary='#1d1d1f',
    text_secondary='#86868b',
    text_tertiary='#aeaeb2',
    text_placeholder='#c7c7cc',

    border_subtle='#e8e8ed',
    border_default='#d2d2d7',
    border_focus='#007aff',

    accent_primary='#007aff',
    accent_secondary='#5ac8fa',

    success='#34c759',
    warning='#ff9500',
    error='#ff3b30',
    info='#5ac8fa',
)


# ============ 单例管理 ============

class StyleManager:
    """样式管理器"""

    def __init__(self, theme: str = 'dark'):
        self._theme = theme
        self.spacing = Spacing()
        self.radius = Radius()
        self.animation = Animation()
        self.sizes = ComponentSizes()
        self.fonts = FontConfig(
            family='Segoe UI',
            fallback='Microsoft YaHei',
            mono='Consolas',
        )

    @property
    def palette(self) -> ColorPalette:
        return DARK_PALETTE if self._theme == 'dark' else LIGHT_PALETTE

    @property
    def theme(self) -> str:
        return self._theme

    def set_theme(self, theme: str):
        object.__setattr__(self, '_theme', theme)

    def get_font(self, size_key: str, weight: str = 'normal') -> tuple:
        """获取 tkinter 字体元组"""
        size = self.fonts.sizes.get(size_key, 12)
        if weight == 'bold':
            return (self.fonts.family, size, 'bold')
        return (self.fonts.family, size)
