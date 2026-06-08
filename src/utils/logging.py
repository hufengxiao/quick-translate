"""Structured logging — loguru with stdlib fallback."""
from __future__ import annotations
import os
import sys
import logging
from pathlib import Path

APP_NAME = "QuickTranslate"
LOG_DIR = Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / APP_NAME / "logs"

# ── Try loguru first ──
try:
    from loguru import logger as _loguru_logger
    _HAS_LOGURU = True
except ImportError:
    _HAS_LOGURU = False


class _StdlibShim:
    """Shim that mimics loguru's .info("msg {}", val) API over stdlib logging."""

    def __init__(self):
        self._logger = logging.getLogger("quick-translate")
        self._logger.setLevel(logging.DEBUG)
        self._configured = False

    def _ensure_handler(self, level="INFO", file_enabled=True, max_size_mb=10):
        self._logger.handlers.clear()  # always reset to allow reconfiguration
        # Console
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(getattr(logging, level.upper(), logging.INFO))
        ch.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s",
                                          datefmt="%H:%M:%S"))
        self._logger.addHandler(ch)
        self._configured = True

    def _fmt(self, msg: str, args: tuple) -> str:
        """Convert loguru-style {} to formatted string."""
        if not args:
            return msg
        try:
            return msg.format(*args)
        except (IndexError, KeyError, ValueError):
            return f"{msg} {args}"

    def debug(self, msg, *args, **kwargs):
        self._logger.debug(self._fmt(msg, args))

    def info(self, msg, *args, **kwargs):
        self._logger.info(self._fmt(msg, args))

    def warning(self, msg, *args, **kwargs):
        self._logger.warning(self._fmt(msg, args))

    def error(self, msg, *args, **kwargs):
        self._logger.error(self._fmt(msg, args))

    def add(self, *a, **kw):
        pass

    def remove(self, *a, **kw):
        pass


if _HAS_LOGURU:
    _base_logger = _loguru_logger
else:
    _base_logger = _StdlibShim()


class _Logger:
    """Unified logger that delegates to loguru or stdlib shim."""

    def __init__(self, base):
        self._base = base

    def debug(self, msg, *a, **kw):
        self._base.debug(msg, *a, **kw)

    def info(self, msg, *a, **kw):
        self._base.info(msg, *a, **kw)

    def warning(self, msg, *a, **kw):
        self._base.warning(msg, *a, **kw)

    def error(self, msg, *a, **kw):
        self._base.error(msg, *a, **kw)

    def add(self, *a, **kw):
        if hasattr(self._base, 'add'):
            self._base.add(*a, **kw)

    def remove(self, *a, **kw):
        if hasattr(self._base, 'remove'):
            self._base.remove(*a, **kw)


logger = _Logger(_base_logger)


def setup_logging(level: str = "INFO", file_enabled: bool = True, max_size_mb: int = 10) -> None:
    """Configure logging with console + optional rotating file."""
    if _HAS_LOGURU:
        # loguru setup
        try:
            logger.remove(0)
        except Exception:
            pass
        logger.add(
            sys.stderr,
            level=level,
            format="<green>{time:HH:mm:ss}</green> | <level>{level:<7}</level> | {message}",
            colorize=True,
        )
        if file_enabled:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            logger.add(
                str(LOG_DIR / "app_{time:YYYY-MM-DD}.log"),
                level="DEBUG",
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<7} | {module}:{function}:{line} | {message}",
                rotation=f"{max_size_mb} MB",
                retention="7 days",
                compression="gz",
                encoding="utf-8",
            )
    else:
        # stdlib shim
        if isinstance(_base_logger, _StdlibShim):
            _base_logger._ensure_handler(level, file_enabled, max_size_mb)

    logger.info("Logging initialized — level={}, file={}", level, file_enabled)
