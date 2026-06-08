"""Lazy loader — high-frequency words first, then background load."""
from __future__ import annotations
import json
import os
import threading
import time
from typing import Callable, Optional

from ...utils.logging import logger
from ...utils.errors import DictionaryError, DictionaryNotFoundError, DictionaryCorruptError


class LazyDictLoader:
    """Two-phase dictionary loader.
    
    Phase 1 (blocking): Load top-N high-frequency words → ready to use in < 100ms
    Phase 2 (background): Load remaining words in a daemon thread
    """

    def __init__(self, dict_path: str, preload_count: int = 10000) -> None:
        self._dict_path = dict_path
        self._preload_count = preload_count
        self._full_data: dict[str, str] = {}
        self._sorted_keys: list[str] = []
        self._phase = 0  # 0=not started, 1=preload done, 2=full load done
        self._load_time_ms = 0.0
        self._on_complete: Optional[Callable[[dict[str, str], list[str]], None]] = None

    @property
    def phase(self) -> int:
        return self._phase

    @property
    def is_fully_loaded(self) -> bool:
        return self._phase == 2

    @property
    def word_count(self) -> int:
        return len(self._full_data)

    @property
    def sorted_keys(self) -> list[str]:
        return self._sorted_keys

    @property
    def data(self) -> dict[str, str]:
        return self._full_data

    def load_sync(self) -> tuple[dict[str, str], list[str]]:
        """Synchronous full load. Used as fallback."""
        self._full_data = self._read_dict_file()
        self._sorted_keys = sorted(self._full_data.keys())
        self._phase = 2
        return self._full_data, self._sorted_keys

    def load_preload_then_background(self, on_complete: Optional[Callable] = None) -> dict[str, str]:
        """Load high-freq words synchronously, then background-load the rest.
        Returns the preload subset immediately."""
        self._on_complete = on_complete
        t0 = time.perf_counter()

        raw = self._read_dict_file()
        all_keys = sorted(raw.keys())
        total = len(all_keys)

        if total <= self._preload_count:
            # Small dict — load everything
            self._full_data = raw
            self._sorted_keys = all_keys
            self._phase = 2
            self._load_time_ms = (time.perf_counter() - t0) * 1000
            logger.info("Dict loaded fully: {} words in {:.1f}ms", total, self._load_time_ms)
            return self._full_data

        # Phase 1: preload first N sorted keys
        preload_keys = all_keys[:self._preload_count]
        preload_data = {k: raw[k] for k in preload_keys}
        self._full_data = preload_data
        self._sorted_keys = preload_keys
        self._phase = 1
        self._load_time_ms = (time.perf_counter() - t0) * 1000
        logger.info("Phase 1 preload: {} words in {:.1f}ms", self._preload_count, self._load_time_ms)

        # Phase 2: background load remaining
        remaining_keys = all_keys[self._preload_count:]
        thread = threading.Thread(
            target=self._background_load,
            args=(raw, remaining_keys, all_keys),
            daemon=True,
        )
        thread.start()

        return self._full_data

    def _background_load(self, raw: dict, remaining_keys: list[str], all_keys: list[str]) -> None:
        t0 = time.perf_counter()
        # Build a NEW dict to avoid mutating the one the main thread is iterating
        full: dict[str, str] = {}
        # Copy preload entries from the current dict
        full.update(self._full_data)
        # Add remaining entries
        for k in remaining_keys:
            full[k] = raw[k]

        # Atomic swap — main thread sees the new dict only when fully built
        self._full_data = full
        self._sorted_keys = all_keys
        self._phase = 2
        elapsed = (time.perf_counter() - t0) * 1000
        logger.info("Phase 2 background: {} words in {:.1f}ms (total={})",
                     len(remaining_keys), elapsed, len(all_keys))

        if self._on_complete:
            self._on_complete(self._full_data, self._sorted_keys)

    def _read_dict_file(self) -> dict[str, str]:
        """Read and parse the dictionary JSON file."""
        if not os.path.exists(self._dict_path):
            raise DictionaryNotFoundError(f"Dictionary not found: {self._dict_path}")
        try:
            with open(self._dict_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            elif isinstance(data, list):
                return {item["word"]: item["definition"] for item in data if "word" in item}
            else:
                raise DictionaryCorruptError(f"Unexpected dict format: {type(data)}")
        except json.JSONDecodeError as e:
            raise DictionaryCorruptError(f"Invalid JSON in {self._dict_path}: {e}")
        except Exception as e:
            raise DictionaryError(f"Failed to load dictionary: {e}")
