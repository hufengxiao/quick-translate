"""AI 翻译引擎模块 - 支持 OpenAI 兼容 API，支持多模型自动切换"""
import urllib.request
import urllib.error
import json
import ssl
import threading
from typing import Optional, Callable


class AITranslator:
    """AI 翻译器，调用 OpenAI 兼容 API（单 provider）"""

    def __init__(self, api_base: str, api_key: str, model: str, system_prompt: str,
                 name: str = ""):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self.name = name or model
        self._busy = False
        self._lock = threading.Lock()

    def translate(self, text: str, callback: Callable[[str], None], error_callback: Optional[Callable[[str], None]] = None):
        """异步翻译文本，结果通过回调返回"""
        with self._lock:
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
            with self._lock:
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


class MultiAITranslator:
    """多 AI 模型翻译器 — 按优先级尝试多个 provider，自动切换失败的模型"""

    def __init__(self, providers: list, system_prompt: str, auto_switch: bool = True):
        """
        Args:
            providers: list of AIProvider-like objects (name, api_base, api_key, model, priority, enabled)
            system_prompt: shared system prompt for all providers
            auto_switch: if True, auto-try next provider on failure
        """
        self._translators: list[AITranslator] = []
        self._auto_switch = auto_switch
        self._busy = False
        self._lock = threading.Lock()
        self._current_index = 0

        for p in providers:
            if not p.enabled:
                continue
            t = AITranslator(
                api_base=p.api_base,
                api_key=p.api_key,
                model=p.model,
                system_prompt=system_prompt,
                name=getattr(p, "name", "") or p.model,
            )
            if t.is_configured:
                self._translators.append(t)

    def translate(self, text: str, callback: Callable[[str], None],
                  error_callback: Optional[Callable[[str], None]] = None):
        """异步翻译文本，失败时自动切换到下一个 provider"""
        with self._lock:
            if self._busy:
                return
            self._busy = True
        thread = threading.Thread(
            target=self._do_translate_with_failover,
            args=(text, callback, error_callback),
            daemon=True,
        )
        thread.start()

    def _do_translate_with_failover(self, text: str, callback, error_callback):
        """尝试所有 provider 直到成功或全部失败"""
        if not self._translators:
            if error_callback:
                error_callback("没有可用的 AI 模型")
            with self._lock:
                self._busy = False
            return

        errors = []
        # Try starting from current index (sticky to last successful provider)
        start = self._current_index % len(self._translators)
        for i in range(len(self._translators)):
            idx = (start + i) % len(self._translators)
            translator = self._translators[idx]
            try:
                result = translator._call_api(text)
                self._current_index = idx  # Stick to successful provider
                callback(result)
                with self._lock:
                    self._busy = False
                return
            except Exception as e:
                errors.append(f"[{translator.name}] {e}")
                if not self._auto_switch:
                    break

        # All providers failed
        if error_callback:
            error_callback("所有 AI 模型都失败:\n" + "\n".join(errors))
        with self._lock:
            self._busy = False

    @property
    def is_busy(self) -> bool:
        return self._busy

    @property
    def is_configured(self) -> bool:
        return len(self._translators) > 0

    @property
    def current_provider_name(self) -> str:
        """当前正在使用的 provider 名称"""
        if not self._translators:
            return ""
        idx = self._current_index % len(self._translators)
        return self._translators[idx].name

    @property
    def provider_count(self) -> int:
        return len(self._translators)

    def get_provider_names(self) -> list[str]:
        return [t.name for t in self._translators]
