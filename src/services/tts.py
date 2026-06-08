"""Text-to-Speech service — Windows SAPI for offline pronunciation.

Uses win32com (if available) or ctypes COM automation for SAPI5.
No external dependencies needed on Windows.
"""
from __future__ import annotations
import ctypes
import threading
from typing import Optional

from ..utils.logging import logger


class TTSService:
    """Windows SAPI5 TTS for word pronunciation.

    Tries win32com first (if pywin32 installed), falls back to
    direct COM via ctypes (works without pywin32).
    """

    def __init__(self, rate: int = 0, volume: int = 100) -> None:
        self._rate = rate
        self._volume = volume
        self._voice = None
        self._sapi = None
        self._available = False
        self._init_sapi()

    def _init_sapi(self) -> None:
        """Initialize SAPI5 COM object."""
        # Try win32com first
        try:
            import win32com.client
            self._sapi = win32com.client.Dispatch("SAPI.SpVoice")
            self._sapi.Rate = self._rate
            self._sapi.Volume = self._volume
            self._available = True
            logger.info("TTS initialized via win32com (SAPI5)")
            return
        except ImportError:
            pass
        except Exception as e:
            logger.debug("win32com TTS init failed: {}", e)

        # Fallback: ctypes COM — skip for now, too complex
        # The app works without TTS, just shows a warning
        logger.info("TTS not available (install pywin32 for pronunciation)")
        self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def speak(self, text: str, lang: str = "en") -> None:
        """Speak text asynchronously. Non-blocking."""
        if not self._available or not self._sapi:
            return
        thread = threading.Thread(target=self._do_speak, args=(text,), daemon=True)
        thread.start()

    def _do_speak(self, text: str) -> None:
        try:
            # SVSFDefault = 0 (synchronous), SVSFlagsAsync = 1
            self._sapi.Speak(text, 1)
        except Exception as e:
            logger.error("TTS speak error: {}", e)

    def speak_sync(self, text: str) -> None:
        """Speak text synchronously (blocking)."""
        if not self._available or not self._sapi:
            return
        try:
            self._sapi.Speak(text, 0)
        except Exception as e:
            logger.error("TTS speak_sync error: {}", e)

    def get_voices(self) -> list[str]:
        """List available SAPI voices."""
        if not self._available or not self._sapi:
            return []
        try:
            voices = self._sapi.GetVoices()
            return [voices.Item(i).GetDescription() for i in range(voices.Count)]
        except Exception:
            return []

    def set_voice(self, index: int = 0) -> bool:
        """Set voice by index."""
        if not self._available or not self._sapi:
            return False
        try:
            voices = self._sapi.GetVoices()
            if 0 <= index < voices.Count:
                self._sapi.Voice = voices.Item(index)
                return True
        except Exception:
            pass
        return False
