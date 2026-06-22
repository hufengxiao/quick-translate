"""
Quick Translate — Crash Report Module
自动收集错误信息，生成结构化崩溃报告。
"""
from __future__ import annotations

import datetime
import json
import os
import platform
import sys
import traceback
from pathlib import Path
from typing import Optional

from .logging import logger

APP_NAME = "QuickTranslate"
_REPORT_DIR = Path(
    os.environ.get("APPDATA", os.path.expanduser("~"))
) / APP_NAME / "crash_reports"

# Keep at most this many crash reports
_MAX_REPORTS = 50


def _collect_system_info() -> dict:
    """Gather platform / environment details."""
    info: dict = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "architecture": platform.machine(),
        "os_name": os.name,
    }
    # Windows-specific extras
    if sys.platform == "win32":
        try:
            info["windows_edition"] = platform.win32_edition()  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            info["windows_version"] = platform.win32_ver()
        except Exception:
            pass

    # Memory (best-effort, no psutil dependency)
    try:
        import ctypes
        class _MemStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
            ]
        mem = _MemStatus()
        mem.dwLength = ctypes.sizeof(_MemStatus())
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
        info["total_memory_mb"] = round(mem.ullTotalPhys / (1024 * 1024))
        info["available_memory_mb"] = round(mem.ullAvailPhys / (1024 * 1024))
        info["memory_load_pct"] = mem.dwMemoryLoad
    except Exception:
        pass

    return info


def _tail_log_file(max_lines: int = 100) -> list[str]:
    """Read the last *max_lines* from today's log file (if any)."""
    from .logging import LOG_DIR
    today = datetime.date.today().strftime("%Y-%m-%d")
    # Try both loguru and stdlib naming conventions
    candidates = [
        LOG_DIR / f"app_{today}.log",
        LOG_DIR / f"{today}.log",
    ]
    for log_file in candidates:
        if log_file.exists():
            try:
                lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
                return lines[-max_lines:]
            except Exception:
                pass
    return []


def generate_crash_report(
    exc_type: Optional[type] = None,
    exc_value: Optional[BaseException] = None,
    exc_tb: Optional[traceback.TracebackException] = None,
    context: str = "",
    extra: Optional[dict] = None,
) -> dict:
    """
    Build a structured crash report dict.
    If exc_type etc. are not supplied, uses the current exception from sys.exc_info().
    """
    if exc_type is None:
        exc_type, exc_value, exc_tb_raw = sys.exc_info()
        if exc_tb_raw is not None:
            exc_tb = traceback.TracebackException(exc_type, exc_value, exc_tb_raw)

    report: dict = {
        "app": APP_NAME,
        "timestamp": datetime.datetime.now().isoformat(),
        "context": context,
        "system": _collect_system_info(),
    }

    if exc_type is not None:
        report["error"] = {
            "type": exc_type.__name__,
            "module": exc_type.__module__,
            "message": str(exc_value) if exc_value else "",
        }
    if exc_tb is not None:
        report["traceback"] = "".join(exc_tb.format())

    # Attach recent log tail
    log_tail = _tail_log_file(80)
    if log_tail:
        report["log_tail"] = log_tail

    if extra:
        report["extra"] = extra

    return report


def save_crash_report(report: dict) -> Path:
    """
    Write crash report to disk and prune old reports.
    Returns the path to the saved file.
    """
    _REPORT_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    err_type = report.get("error", {}).get("type", "unknown")
    filename = f"crash_{ts}_{err_type}.json"
    filepath = _REPORT_DIR / filename

    filepath.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    logger.error("Crash report saved: {}", filepath)

    # Prune old reports
    _prune_reports()

    return filepath


def _prune_reports() -> None:
    """Keep at most _MAX_REPORTS crash reports, deleting oldest first."""
    try:
        reports = sorted(_REPORT_DIR.glob("crash_*.json"), key=lambda p: p.stat().st_mtime)
        excess = len(reports) - _MAX_REPORTS
        for old in reports[:excess]:
            old.unlink(missing_ok=True)
    except Exception:
        pass


def collect_and_save(
    exc_type: Optional[type] = None,
    exc_value: Optional[BaseException] = None,
    exc_tb: Optional[traceback.TracebackException] = None,
    context: str = "",
    extra: Optional[dict] = None,
) -> Path:
    """
    Convenience: generate + save in one call.
    Returns path to saved report.
    """
    report = generate_crash_report(exc_type, exc_value, exc_tb, context, extra)
    return save_crash_report(report)


def get_report_dir() -> Path:
    """Return the crash reports directory path."""
    return _REPORT_DIR


def list_reports(limit: int = 10) -> list[Path]:
    """Return the most recent crash report files (newest first)."""
    if not _REPORT_DIR.exists():
        return []
    reports = sorted(_REPORT_DIR.glob("crash_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return reports[:limit]
