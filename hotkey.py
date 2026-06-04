"""全局热键监听模块 - 使用 Windows RegisterHotKey API"""
import ctypes
import ctypes.wintypes as wintypes
import threading

# Windows constants
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
VK_M = 0x4D

user32 = ctypes.windll.user32
HOTKEY_ID = 1


class HotkeyListener:
    """全局热键监听器，通过 RegisterHotKey 注册系统级热键"""

    def __init__(self, shift=True, ctrl=True, alt=False, win=False, key="m", callback=None):
        self.modifiers = 0
        if shift:
            self.modifiers |= MOD_SHIFT
        if ctrl:
            self.modifiers |= MOD_CONTROL
        if alt:
            self.modifiers |= MOD_ALT
        if win:
            self.modifiers |= MOD_WIN

        self.vk = ord(key.upper()) if isinstance(key, str) and len(key) == 1 else VK_M
        self.callback = callback
        self._running = False
        self._thread = None

    def start(self):
        """注册热键并启动消息循环线程"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._message_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止监听并注销热键"""
        self._running = False
        # post WM_QUIT to break the message loop
        user32.PostThreadMessageW(self._thread.ident, 0x0012, 0, 0)  # WM_QUIT

    def _message_loop(self):
        """在独立线程中运行 Windows 消息循环"""
        if not user32.RegisterHotKey(None, HOTKEY_ID, self.modifiers, self.vk):
            # Hotkey already registered or failed
            print(f"[Hotkey] Failed to register hotkey (mod={self.modifiers:#x}, vk={self.vk:#x})")
            self._running = False
            return

        print(f"[Hotkey] Registered: Shift+Ctrl+M (id={HOTKEY_ID})")
        msg = wintypes.MSG()

        while self._running:
            # GetMessage blocks until a message arrives
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret == 0 or ret == -1:
                break
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                if self.callback:
                    # Use tkinter's after() from the callback if needed
                    self.callback()

        user32.UnregisterHotKey(None, HOTKEY_ID)
        print("[Hotkey] Unregistered")
