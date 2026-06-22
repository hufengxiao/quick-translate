"""Detect Windows system dark/light theme preference.

Reads the registry key:
  HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize\AppsUseLightTheme

Returns 'dark' or 'light'.
"""
import sys


def get_system_theme() -> str:
    """Return the current Windows system theme: 'dark' or 'light'.

    Falls back to 'dark' on non-Windows or if the registry key is missing.
    """
    if sys.platform != 'win32':
        return 'dark'
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize',
        )
        value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
        winreg.CloseKey(key)
        return 'light' if value == 1 else 'dark'
    except Exception:
        return 'dark'
