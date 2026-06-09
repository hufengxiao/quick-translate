"""
Quick Translate 错误处理模块
自动分类、用户友好消息、重试装饰器
"""
import functools
import time
import logging
import traceback
from typing import Callable, Optional, Any
from enum import Enum

logger = logging.getLogger('QuickTranslate')


class ErrorType(Enum):
    """错误类型分类"""
    NETWORK = "network"
    API = "api"
    DICTIONARY = "dictionary"
    UI = "ui"
    HOTKEY = "hotkey"
    CLIPBOARD = "clipboard"
    DATABASE = "database"
    UNKNOWN = "unknown"


# 用户友好消息映射
USER_MESSAGES = {
    ErrorType.NETWORK: "网络连接失败，请检查网络设置",
    ErrorType.API: "翻译服务暂时不可用，请稍后重试",
    ErrorType.DICTIONARY: "词典加载失败，请检查词典文件",
    ErrorType.UI: "界面显示异常",
    ErrorType.HOTKEY: "快捷键注册失败，可能被其他程序占用",
    ErrorType.CLIPBOARD: "剪贴板访问失败",
    ErrorType.DATABASE: "数据存储异常",
    ErrorType.UNKNOWN: "发生未知错误",
}


def classify_error(error: Exception) -> ErrorType:
    """自动分类错误类型"""
    error_str = str(error).lower()
    type_name = type(error).__name__.lower()

    if 'timeout' in error_str or 'connection' in error_str or 'network' in error_str:
        return ErrorType.NETWORK
    if 'api' in error_str or 'http' in type_name or 'url' in type_name:
        return ErrorType.API
    if 'dict' in error_str or 'json' in type_name:
        return ErrorType.DICTIONARY
    if 'hotkey' in error_str or 'register' in error_str:
        return ErrorType.HOTKEY
    if 'clipboard' in error_str:
        return ErrorType.CLIPBOARD
    if 'sqlite' in error_str or 'database' in error_str:
        return ErrorType.DATABASE
    if 'tkinter' in error_str or 'tcl' in error_str:
        return ErrorType.UI

    return ErrorType.UNKNOWN


def get_user_message(error: Exception) -> str:
    """获取用户友好的错误消息"""
    error_type = classify_error(error)
    return USER_MESSAGES.get(error_type, USER_MESSAGES[ErrorType.UNKNOWN])


def retry(max_attempts: int = 3, delay: float = 1.0,
          backoff: float = 2.0, exceptions: tuple = (Exception,)):
    """重试装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"{func.__name__} 第 {attempt + 1} 次失败: {e}，"
                            f"{current_delay:.1f}s 后重试"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"{func.__name__} {max_attempts} 次尝试均失败: {e}"
                        )
            raise last_error
        return wrapper
    return decorator


class ErrorHandler:
    """错误处理器"""

    def __init__(self, show_toast: Optional[Callable] = None):
        self.show_toast = show_toast

    def handle(self, error: Exception, context: str = ""):
        """处理错误"""
        error_type = classify_error(error)
        user_msg = get_user_message(error)

        # 记录详细日志
        logger.error(
            f"[{error_type.value}] {context}: {error}\n"
            f"{traceback.format_exc()}"
        )

        # 显示用户提示
        if self.show_toast:
            self.show_toast(f"⚠ {user_msg}", 3000)

        return error_type
