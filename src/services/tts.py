"""Text-to-Speech service — Windows pronunciation via multiple backends.

Priority: PowerShell System.Speech > subprocess SAPI > disabled.
No pywin32 dependency needed.
"""
from __future__ import annotations
import subprocess
import threading
from typing import Optional

from ..utils.logging import logger


class TTSService:
    """Windows TTS for word pronunciation.

    Uses PowerShell System.Speech (reliable, no COM registration issues).
    Falls back to subprocess if needed.
    """

    def __init__(self, rate: int = 0, volume: int = 100) -> None:
        self._rate = rate
        self._volume = volume
        self._available = False
        self._backend = "none"
        self._check_availability()

    def _check_availability(self) -> None:
        """Test if TTS works on this system."""
        # Try PowerShell System.Speech
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Dispose(); Write-Host OK"],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if "OK" in result.stdout:
                self._available = True
                self._backend = "powershell"
                logger.info("TTS available via PowerShell System.Speech")
                return
        except Exception as e:
            logger.debug("PowerShell TTS check failed: {}", e)

        logger.info("TTS not available on this system")
        self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def speak(self, text: str, lang: str = "en") -> None:
        """Speak text asynchronously (non-blocking)."""
        if not self._available:
            return
        thread = threading.Thread(target=self._do_speak, args=(text,), daemon=True)
        thread.start()

    def _do_speak(self, text: str) -> None:
        """Speak using PowerShell System.Speech."""
        try:
            # Escape single quotes in text
            safe_text = text.replace("'", "''")
            script = (
                "Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$s.Rate = {self._rate}; "
                f"$s.Volume = {self._volume}; "
                f"$s.Speak('{safe_text}'); "
                "$s.Dispose()"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True, timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except subprocess.TimeoutExpired:
            logger.warning("TTS speak timed out")
        except Exception as e:
            logger.error("TTS speak error: {}", e)

    def get_voices(self) -> list[str]:
        """List available voices."""
        if not self._available:
            return []
        try:
            script = (
                "Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$s.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }; "
                "$s.Dispose()"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        except Exception:
            return []
