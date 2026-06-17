"""自动更新检测 — 检查 GitHub Releases 获取新版本"""
import json
import os
import urllib.request
import ssl
import threading
from typing import Optional, Callable

CURRENT_VERSION = "1.2.0"
GITHUB_API = "https://api.github.com/repos/hufengxiao/quick-translate/releases/latest"
CHECK_INTERVAL = 86400  # 24 hours


class UpdateChecker:
    """Check for updates from GitHub Releases."""

    def __init__(self, on_update: Optional[Callable[[str, str], None]] = None):
        """
        Args:
            on_update: callback(latest_version, download_url) when update found
        """
        self._on_update = on_update
        self._last_check = 0
        self._latest: Optional[str] = None
        self._url: Optional[str] = None

    def check_async(self) -> None:
        """Check for updates in background thread."""
        now = time.time()
        if now - self._last_check < CHECK_INTERVAL:
            return
        self._last_check = now
        thread = threading.Thread(target=self._do_check, daemon=True)
        thread.start()

    def _do_check(self) -> None:
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(GITHUB_API)
            req.add_header("User-Agent", "QuickTranslate")
            req.add_header("Accept", "application/vnd.github.v3+json")

            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            tag = data.get("tag_name", "").lstrip("v")
            if tag and self._is_newer(tag, CURRENT_VERSION):
                self._latest = tag
                self._url = data.get("html_url", "")
                if self._on_update:
                    self._on_update(tag, self._url)
        except Exception:
            pass  # Silent fail — don't bother user

    @staticmethod
    def _is_newer(latest: str, current: str) -> bool:
        """Compare semver strings."""
        try:
            l = [int(x) for x in latest.split(".")]
            c = [int(x) for x in current.split(".")]
            return l > c
        except (ValueError, AttributeError):
            return False

    @property
    def has_update(self) -> bool:
        return self._latest is not None

    @property
    def latest_version(self) -> Optional[str]:
        return self._latest

    @property
    def download_url(self) -> Optional[str]:
        return self._url
