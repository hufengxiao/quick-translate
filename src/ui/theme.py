"""Theme system — Apple HIG-inspired dark/light palettes for tkinter."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """Complete color + font theme."""
    name: str
    # Backgrounds
    bg: str           # Main window background
    surface: str      # Cards / panels
    surface2: str     # Elevated surfaces (entry, hover)
    # Text
    fg: str           # Primary text
    fg_secondary: str # Secondary / muted text
    fg_tertiary: str  # Hint text
    # Accent
    accent: str       # Selection, links, active
    accent_hover: str # Hover state
    accent_pressed: str
    # Semantic
    success: str
    warning: str
    error: str
    # Separators
    separator: str
    # Input
    entry_bg: str
    entry_fg: str
    entry_placeholder: str
    # List
    list_bg: str
    list_hover: str
    list_selected_bg: str
    list_selected_fg: str
    # Scrollbar
    scrollbar_bg: str
    scrollbar_fg: str
    # Toast
    toast_bg: str
    toast_fg: str


# ── Dark Theme (default) — Apple Dark Mode ──
DARK = Theme(
    name="dark",
    bg="#1C1C1E",
    surface="#2C2C2E",
    surface2="#3A3A3C",
    fg="#F5F5F7",
    fg_secondary="#98989D",
    fg_tertiary="#636366",
    accent="#0A84FF",
    accent_hover="#409CFF",
    accent_pressed="#0077ED",
    success="#30D158",
    warning="#FFD60A",
    error="#FF453A",
    separator="#38383A",
    entry_bg="#2C2C2E",
    entry_fg="#F5F5F7",
    entry_placeholder="#636366",
    list_bg="#1C1C1E",
    list_hover="#2C2C2E",
    list_selected_bg="#0A84FF",
    list_selected_fg="#FFFFFF",
    scrollbar_bg="#1C1C1E",
    scrollbar_fg="#48484A",
    toast_bg="#3A3A3C",
    toast_fg="#F5F5F7",
)

# ── Light Theme ──
LIGHT = Theme(
    name="light",
    bg="#FFFFFF",
    surface="#F2F2F7",
    surface2="#E5E5EA",
    fg="#1C1C1E",
    fg_secondary="#8E8E93",
    fg_tertiary="#AEAEB2",
    accent="#007AFF",
    accent_hover="#5AC8FA",
    accent_pressed="#0056B3",
    success="#34C759",
    warning="#FF9500",
    error="#FF3B30",
    separator="#D1D1D6",
    entry_bg="#E5E5EA",
    entry_fg="#1C1C1E",
    entry_placeholder="#AEAEB2",
    list_bg="#FFFFFF",
    list_hover="#F2F2F7",
    list_selected_bg="#007AFF",
    list_selected_fg="#FFFFFF",
    scrollbar_bg="#FFFFFF",
    scrollbar_fg="#C7C7CC",
    toast_bg="#3A3A3C",
    toast_fg="#F5F5F7",
)


# -- High Contrast Theme (accessibility) --
HIGH_CONTRAST = Theme(
    name="high_contrast",
    bg="#000000",
    surface="#1A1A1A",
    surface2="#333333",
    fg="#FFFFFF",
    fg_secondary="#CCCCCC",
    fg_tertiary="#999999",
    accent="#FFD700",
    accent_hover="#FFF080",
    accent_pressed="#FFC000",
    success="#00FF00",
    warning="#FFFF00",
    error="#FF0000",
    separator="#666666",
    entry_bg="#1A1A1A",
    entry_fg="#FFFFFF",
    entry_placeholder="#999999",
    list_bg="#000000",
    list_hover="#333333",
    list_selected_bg="#FFD700",
    list_selected_fg="#000000",
    scrollbar_bg="#000000",
    scrollbar_fg="#666666",
    toast_bg="#333333",
    toast_fg="#FFFFFF",
)

THEMES: dict[str, Theme] = {"dark": DARK, "light": LIGHT, "high_contrast": HIGH_CONTRAST}


def get_theme(name: str = "dark") -> Theme:
    return THEMES.get(name, DARK)
