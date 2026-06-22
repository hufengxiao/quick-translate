"""Auto-start on Windows boot via registry."""
import sys
import os

_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "QuickTranslate"


def _get_exe_path() -> str:
    """Return the path of the running executable (or python script)."""
    if getattr(sys, "frozen", False):
        # PyInstaller bundle
        return sys.executable
    return os.path.abspath(sys.argv[0])


def is_autostart_enabled() -> bool:
    """Check if auto-start is currently registered."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0,
                             winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, _VALUE_NAME)
            return bool(val)
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def enable_autostart() -> bool:
    """Register the app to start with Windows. Returns True on success."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0,
                             winreg.KEY_SET_VALUE)
        exe_path = _get_exe_path()
        winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ,
                          f'"{exe_path}"')
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def disable_autostart() -> bool:
    """Remove the auto-start registry entry. Returns True on success."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0,
                             winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, _VALUE_NAME)
        except FileNotFoundError:
            pass  # already removed
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def set_autostart(enabled: bool) -> bool:
    """Enable or disable auto-start. Returns True on success."""
    if enabled:
        return enable_autostart()
    else:
        return disable_autostart()
