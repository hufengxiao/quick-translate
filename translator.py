"""AI 翻译引擎模块 - 支持 OpenAI 兼容 API"""
import urllib.request
import urllib.error
import json
import ssl
import threading
from typing import Optional, Callable


class AITranslator:
    """AI 翻译器，调用 OpenAI 兼容 API"""

    def __init__(self, api_base: str, api_key: str, model: str, system_prompt: str):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self._busy = False

    def translate(self, text: str, callback: Callable[[str], None], error_callback: Optional[Callable[[str], None]] = None):
        """异步翻译文本，结果通过回调返回"""
        if self._busy:
            return
        self._busy = True
        thread = threading.Thread(
            target=self._do_translate,
            args=(text, callback, error_callback),
            daemon=True,
        )
        thread.start()

    def _do_translate(self, text: str, callback, error_callback):
        try:
            result = self._call_api(text)
            callback(result)
        except Exception as e:
            if error_callback:
                error_callback(str(e))
        finally:
            self._busy = False

    def _call_api(self, text: str) -> str:
        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": text},
            ],
            "temperature": 0.3,
            "max_tokens": 2048,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")

        # Allow self-signed certs for local APIs
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        try:
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            raise RuntimeError(f"API error {e.code}: {error_body[:200]}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Network error: {e.reason}")

    @property
    def is_busy(self) -> bool:
        return self._busy

    @property
    def is_configured(self) -> bool:
        return bool(self.api_base and self.model)
