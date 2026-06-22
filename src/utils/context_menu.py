"""Windows right-click context menu integration.

Registers a shell context menu entry so users can right-click selected text
(or files) and choose "用 Quick Translate 翻译" to look it up.

On Windows, the registry creates entries under:
  HKCU\\Software\\Classes\\*\\shell\\QuickTranslate        (files)
  HKCU\\Software\\Classes\\Directory\\shell\\QuickTranslate (folders)

When triggered, the app is launched with --translate "<selected_text>".
For text selections, the handler copies the current selection to clipboard
via a small helper script, then passes the clipboard content.
"""
import sys
import os

_REG_BASE = r"Software\Classes\*\shell\QuickTranslate"
_REG_DIR = r"Software\Classes\Directory\shell\QuickTranslate"
_REG_COMMAND = r"{}\command".format(_REG_BASE)
_REG_DIR_COMMAND = r"{}\command".format(_REG_DIR)
_VALUE_DISPLAY = "用 Quick Translate 翻译"


def _get_exe_path() -> str:
    """Return the path of the running executable (or python script)."""
    if getattr(sys, "frozen", False):
        # PyInstaller bundle
        return sys.executable
    return os.path.abspath(sys.argv[0])


def is_installed() -> bool:
    """Check if the context menu entry is currently registered."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_BASE, 0,
                             winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, "")
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def install() -> bool:
    """Register the context menu entry. Returns True on success."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        exe_path = _get_exe_path()

        # File context menu
        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _REG_BASE, 0,
                                 winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, _VALUE_DISPLAY)
        winreg.CloseKey(key)

        cmd_key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                                     _REG_COMMAND, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ,
                          f'"{exe_path}" --translate "%1"')
        winreg.CloseKey(cmd_key)

        # Directory context menu
        dir_key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _REG_DIR, 0,
                                     winreg.KEY_SET_VALUE)
        winreg.SetValueEx(dir_key, "", 0, winreg.REG_SZ, _VALUE_DISPLAY)
        winreg.CloseKey(dir_key)

        dir_cmd_key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                                         _REG_DIR_COMMAND, 0,
                                         winreg.KEY_SET_VALUE)
        winreg.SetValueEx(dir_cmd_key, "", 0, winreg.REG_SZ,
                          f'"{exe_path}" --translate "%1"')
        winreg.CloseKey(dir_cmd_key)

        return True
    except Exception:
        return False


def uninstall() -> bool:
    """Remove the context menu entry. Returns True on success."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        # Delete command subkey first, then parent (files)
        _delete_tree(_REG_COMMAND)
        _delete_tree(_REG_BASE)

        # Delete command subkey first, then parent (directories)
        _delete_tree(_REG_DIR_COMMAND)
        _delete_tree(_REG_DIR)

        return True
    except Exception:
        return False


def set_enabled(enabled: bool) -> bool:
    """Enable or disable the context menu. Returns True on success."""
    if enabled:
        return install()
    else:
        return uninstall()


def _delete_tree(key_path: str):
    """Delete a registry key tree. Silently ignores missing keys."""
    if sys.platform != "win32":
        return
    try:
        import winreg
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
    except FileNotFoundError:
        pass
    except OSError:
        pass
