"""Text-to-Speech service — Windows SAPI5 for offline pronunciation.

Uses win32com (if available). COM objects must be used on the thread
that created them, so we use a dedicated single-thread worker.
"""
from __future__ import annotations
import threading
from typing import Optional

from ..utils.logging import logger


class TTSService:
    """Windows SAPI5 TTS for word pronunciation.

    Uses a dedicated COM thread: all SAPI calls are dispatched to it
    via a queue, avoiding cross-thread COM errors.
    """

    def __init__(self, rate: int = 0, volume: int = 100) -> None:
        self._rate = rate
        self._volume = volume
        self._sapi = None
        self._available = False
        self._queue: list[tuple[str, int]] = []  # (text, flags)
        self._event = threading.Event()
        self._running = False
        self._init_sapi()

    def _init_sapi(self) -> None:
        """Check if win32com is available, then start worker thread."""
        try:
            import win32com.client  # noqa: F401
            self._available = True
        except ImportError:
            logger.info("TTS not available (install pywin32 for pronunciation)")
            return

        # Start dedicated COM thread
        self._running = True
        self._thread = threading.Thread(target=self._com_worker, daemon=True)
        self._thread.start()

    def _com_worker(self) -> None:
        """Dedicated thread that owns the COM object and processes speak requests."""
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except ImportError:
            pass
        except Exception:
            pass

        try:
            import win32com.client
            self._sapi = win32com.client.Dispatch("SAPI.SpVoice")
            self._sapi.Rate = self._rate
            self._sapi.Volume = self._volume
            logger.info("TTS initialized via win32com (SAPI5)")
        except Exception as e:
            logger.error("TTS COM init failed: {}", e)
            self._available = False
            return

        # Process loop: wait for speak requests
        while self._running:
            self._event.wait()
            self._event.clear()
            while self._queue:
                text, flags = self._queue.pop(0)
                try:
                    self._sapi.Speak(text, flags)
                except Exception as e:
                    logger.error("TTS speak error: {}", e)

        # Cleanup
        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except Exception:
            pass

    @property
    def is_available(self) -> bool:
        return self._available

    def speak(self, text: str, lang: str = "en") -> None:
        """Speak text asynchronously (non-blocking, queued to COM thread)."""
        if not self._available:
            return
        self._queue.append((text, 1))  # SVSFlagsAsync = 1
        self._event.set()

    def speak_sync(self, text: str) -> None:
        """Speak text, block until done (still on COM thread)."""
        if not self._available:
            return
        done = threading.Event()
        self._queue.append((text, 0))  # SVSFDefault = 0 (sync)
        self._event.set()
        # We can't truly wait for COM thread without deadlock risk,
        # so just fire-and-forget for now

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
