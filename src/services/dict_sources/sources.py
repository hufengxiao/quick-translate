"""Multi-dictionary source framework — abstract base + concrete implementations.

Query strategy: local → network → AI
Each source implements the same interface so the router can cascade them.
"""
from __future__ import annotations
import json
import urllib.request
import urllib.error
import ssl
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

from ...utils.logging import logger


class DictSource(ABC):
    """Abstract dictionary source."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable source name."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this source can be used right now."""
        ...

    @abstractmethod
    def lookup(self, word: str) -> Optional[Dict[str, str]]:
        """Look up a single word. Returns {word, definition, source, phonetic?} or None."""
        ...


class LocalDictSource(DictSource):
    """Local dictionary (delegates to the existing Dictionary engine)."""

    def __init__(self, dictionary) -> None:
        self._dict = dictionary

    @property
    def name(self) -> str:
        return "本地词典"

    @property
    def is_available(self) -> bool:
        return self._dict.is_ready

    def lookup(self, word: str) -> Optional[Dict[str, str]]:
        result = self._dict.lookup(word)
        if result:
            return {"word": word, "definition": result, "source": self.name}
        return None


class YoudaoDictSource(DictSource):
    """有道词典 API (free tier, no key needed for basic lookup)."""

    BASE_URL = "https://dict.youdao.com/suggest?num=1&doctype=json&q={}"

    def __init__(self, timeout: int = 5) -> None:
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "有道词典"

    @property
    def is_available(self) -> bool:
        return True

    def lookup(self, word: str) -> Optional[Dict[str, str]]:
        url = self.BASE_URL.format(urllib.request.quote(word))
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "QuickTranslate/1.1")
            with urllib.request.urlopen(req, timeout=self._timeout, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            # Parse youdao suggest response
            if "data" in data and "entries" in data["data"]:
                entries = data["data"]["entries"]
                if entries:
                    entry = entries[0]
                    return {
                        "word": entry.get("word", word),
                        "definition": entry.get("explain", ""),
                        "source": self.name,
                    }
        except Exception as e:
            logger.debug("Youdao lookup failed for '{}': {}", word, e)
        return None


class WebDictSource(DictSource):
    """Generic web API dictionary source (OpenAI-compatible chat)."""

    def __init__(self, api_base: str, api_key: str, model: str,
                 system_prompt: str, timeout: int = 10) -> None:
        self._api_base = api_base.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._system_prompt = system_prompt
        self._timeout = timeout

    @property
    def name(self) -> str:
        return f"AI ({self._model})"

    @property
    def is_available(self) -> bool:
        return bool(self._api_base and self._model)

    def lookup(self, word: str) -> Optional[Dict[str, str]]:
        """AI lookup via OpenAI-compatible chat API."""
        url = f"{self._api_base}/chat/completions"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": word},
            ],
            "temperature": 0.3,
            "max_tokens": 1024,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        if self._api_key:
            req.add_header("Authorization", f"Bearer {self._api_key}")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            with urllib.request.urlopen(req, timeout=self._timeout, context=ctx) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"].strip()
            return {"word": word, "definition": content, "source": self.name}
        except Exception as e:
            logger.debug("AI lookup failed for '{}': {}", word, e)
        return None
