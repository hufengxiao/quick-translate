"""Unified error hierarchy for Quick Translate."""
from __future__ import annotations


class TranslateError(Exception):
    """Base error for all Quick Translate errors."""
    code: str = "UNKNOWN"
    recoverable: bool = True

    def __init__(self, message: str, *, code: str | None = None, recoverable: bool = True):
        super().__init__(message)
        if code:
            self.code = code
        self.recoverable = recoverable


class DictionaryError(TranslateError):
    """Dictionary loading or lookup errors."""
    code = "DICT_ERROR"


class DictionaryNotFoundError(DictionaryError):
    """Dictionary file not found."""
    code = "DICT_NOT_FOUND"
    recoverable = False


class DictionaryCorruptError(DictionaryError):
    """Dictionary file is corrupted or invalid."""
    code = "DICT_CORRUPT"
    recoverable = False


class NetworkError(TranslateError):
    """Network request failures."""
    code = "NETWORK_ERROR"


class APIError(TranslateError):
    """API call errors (rate limit, auth, server error)."""
    code = "API_ERROR"

    def __init__(self, message: str, *, status_code: int | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.status_code = status_code


class ConfigError(TranslateError):
    """Configuration validation errors."""
    code = "CONFIG_ERROR"
    recoverable = False


class CacheError(TranslateError):
    """Cache operation errors."""
    code = "CACHE_ERROR"
