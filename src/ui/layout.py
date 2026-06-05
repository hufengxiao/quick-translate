"""Layout constants — 8px grid system following Apple HIG."""
from __future__ import annotations


class Spacing:
    """8px base grid spacing."""
    UNIT = 8
    XS = 4       # 0.5 unit
    SM = 8       # 1 unit
    MD = 12      # 1.5 units
    LG = 16      # 2 units
    XL = 20      # 2.5 units
    XXL = 24     # 3 units
    XXXL = 32    # 4 units


class Sizes:
    """Component sizes."""
    WINDOW_WIDTH = 360
    WINDOW_HEIGHT = 520
    SEARCH_HEIGHT = 44      # Apple HIG minimum touch target
    TOP_BAR_HEIGHT = 32
    LIST_ITEM_HEIGHT = 36
    CORNER_RADIUS = 12      # Windows 11 style
    ICON_BUTTON = 28


class Fonts:
    """Font specifications."""
    FAMILY = "Segoe UI Variable"
    FAMILY_FALLBACK = "Segoe UI"
    FAMILY_CJK = "Microsoft YaHei UI"
    FAMILY_MONO = "Cascadia Code"
    FAMILY_MONO_FALLBACK = "Consolas"

    SIZE_SEARCH = 14
    SIZE_BODY = 13
    SIZE_CAPTION = 11
    SIZE_TITLE = 15
    SIZE_LARGE = 28
