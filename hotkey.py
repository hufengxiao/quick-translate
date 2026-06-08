"""全局热键监听模块 - 使用 Windows RegisterHotKey API"""
import ctypes
import ctypes.wintypes as wintypes
import threading
import time

# Windows constants
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
VK_M = 0x4D

user32 = ctypes.windll.user32
HOTKEY_ID = 1


class HotkeyListener:
    """全局热键监听器"""

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
        self._thread_id = None
        self._ready = threading.Event()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._message_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._ready.wait(timeout=2.0)  # wait for message loop to be ready
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)

    def _message_loop(self):
        # 必须先确保线程有消息队列
        # 调用 PeekMessage 会强制创建消息队列
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)
        time.sleep(0.05)

        # 记录线程 ID 供 stop() 使用
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        self._ready.set()  # signal that message loop is ready

        if not user32.RegisterHotKey(None, HOTKEY_ID, self.modifiers, self.vk):
            print(f"[Hotkey] Failed to register hotkey (mod={self.modifiers:#x}, vk={self.vk:#x})")
            print(f"[Hotkey] Shift+Ctrl+M may be occupied by another app")
            self._running = False
            return

        print(f"[Hotkey] Registered: Shift+Ctrl+M (id={HOTKEY_ID})")

        while self._running:
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret == 0 or ret == -1:
                break
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                if self.callback:
                    self.callback()

        user32.UnregisterHotKey(None, HOTKEY_ID)
        print("[Hotkey] Unregistered")
