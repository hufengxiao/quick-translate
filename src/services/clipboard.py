"""Clipboard monitoring service — auto-detect copied text for translation.

Uses Win32 clipboard chain (AddClipboardFormatListener) for efficient
notification-based monitoring, with fallback to polling.
"""
from __future__ import annotations
import ctypes
import ctypes.wintypes as wintypes
import re
import threading
import time
from typing import Callable, Optional

from ..utils.logging import logger

# Win32 constants
WM_CLIPBOARDUPDATE = 0x031D
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_QUIT = 0x0012

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Patterns to ignore (URLs, numbers, code snippets)
_IGNORE_PATTERNS = [
    re.compile(r"^https?://"),
    re.compile(r"^\d+(\.\d+)?$"),
    re.compile(r"^[{}\[\]();,.<>]+$"),
    re.compile(r"^\s*$"),
]


class ClipboardMonitor:
    """Monitor clipboard for new text and trigger translation callback.

    Two modes:
    - Win32 event-based (preferred): AddClipboardFormatListener
    - Polling fallback: check every N ms
    """

    def __init__(self, on_text: Callable[[str], None], *,
                 min_length: int = 2,
                 ignore_patterns: list[re.Pattern] | None = None,
                 auto_translate: bool = True) -> None:
        self._on_text = on_text
        self._min_length = min_length
        self._patterns = ignore_patterns or _IGNORE_PATTERNS
        self._auto_translate = auto_translate
        self._running = False
        self._last_text = ""
        self._thread: threading.Thread | None = None
        self._hwnd = None

    def start(self) -> None:
        if self._running or not self._auto_translate:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Clipboard monitor started (min_length={})", self._min_length)

    def stop(self) -> None:
        self._running = False
        if self._hwnd:
            user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)
            self._hwnd = None
        logger.info("Clipboard monitor stopped")

    def _should_ignore(self, text: str) -> bool:
        if len(text) < self._min_length:
            return True
        if len(text) > 500:  # too long, probably not a word/phrase
            return True
        for pat in self._patterns:
            if pat.match(text):
                return True
        return False

    def _get_clipboard_text(self) -> str:
        """Read text from clipboard via Win32 API."""
        try:
            if not user32.OpenClipboard(0):
                return ""
            try:
                CF_UNICODETEXT = 13
                handle = user32.GetClipboardData(CF_UNICODETEXT)
                if not handle:
                    return ""
                ptr = kernel32.GlobalLock(handle)
                if not ptr:
                    return ""
                try:
                    text = ctypes.c_wchar_p(ptr).value or ""
                    return text.strip()
                finally:
                    kernel32.GlobalUnlock(handle)
            finally:
                user32.CloseClipboard()
        except Exception:
            return ""

    def _run(self) -> None:
        """Event-based clipboard monitoring using AddClipboardFormatListener."""
        # Create a hidden window to receive messages
        class_name = "QtClipMon"

        WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND,
                                      wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == WM_CLIPBOARDUPDATE:
                self._check_clipboard()
                return 0
            elif msg == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wndproc_ref = WNDPROC(wnd_proc)
        hinstance = kernel32.GetModuleHandleW(None)

        # Register window class
        wc = wintypes.WNDCLASSEX()
        wc.cbSize = ctypes.sizeof(wintypes.WNDCLASSEX)
        wc.lpfnWndProc = self._wndproc_ref
        wc.hInstance = hinstance
        wc.lpszClassName = class_name
        atom = user32.RegisterClassExW(ctypes.byref(wc))
        if not atom:
            logger.warning("Clipboard monitor: RegisterClassEx failed, falling back to polling")
            self._run_polling()
            return

        self._hwnd = user32.CreateWindowExW(
            0, class_name, "QtClipMon", 0,
            0, 0, 0, 0, 0, 0, hinstance, None,
        )
        if not self._hwnd:
            logger.warning("Clipboard monitor: CreateWindowEx failed, falling back to polling")
            self._run_polling()
            return

        # Register for clipboard notifications
        if not ctypes.windll.user32.AddClipboardFormatListener(self._hwnd):
            logger.warning("Clipboard monitor: AddClipboardFormatListener failed, falling back to polling")
            self._run_polling()
            return

        logger.debug("Clipboard monitor: using Win32 event mode")

        # Message loop
        msg = wintypes.MSG()
        while self._running:
            ret = user32.GetMessageW(ctypes.byref(msg), self._hwnd, 0, 0)
            if ret == 0 or ret == -1:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        # Cleanup
        ctypes.windll.user32.RemoveClipboardFormatListener(self._hwnd)
        user32.DestroyWindow(self._hwnd)

    def _run_polling(self) -> None:
        """Fallback: poll clipboard every 500ms."""
        logger.debug("Clipboard monitor: using polling mode (500ms)")
        while self._running:
            self._check_clipboard()
            time.sleep(0.5)

    def _check_clipboard(self) -> None:
        text = self._get_clipboard_text()
        if not text or text == self._last_text:
            return
        self._last_text = text
        if self._should_ignore(text):
            return
        logger.info("Clipboard detected: {}", text[:50])
        try:
            self._on_text(text)
        except Exception as e:
            logger.error("Clipboard callback error: {}", e)
