"""Windows 系统托盘图标 - 纯 ctypes 实现，零依赖"""
import ctypes
import ctypes.wintypes as wintypes
import threading

# Windows constants
NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
WM_USER = 0x0400
WM_TRAYICON = WM_USER + 1
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
IDI_APPLICATION = 32512
CS_HREDRAW = 0x0002
CS_VREDRAW = 0x0001
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_COMMAND = 0x0111

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32


# 手动定义 WNDCLASSEX 结构体（ctypes.wintypes 不自带）
class WNDCLASSEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("style", ctypes.c_uint),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HANDLE),
        ("hIcon", wintypes.HANDLE),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HANDLE),
        ("lpszMenuName", ctypes.c_wchar_p),
        ("lpszClassName", ctypes.c_wchar_p),
        ("hIconSm", wintypes.HANDLE),
    ]


class NOTIFYICONDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("hWnd", wintypes.HWND),
        ("uID", ctypes.c_uint),
        ("uFlags", ctypes.c_uint),
        ("uCallbackMessage", ctypes.c_uint),
        ("hIcon", wintypes.HWND),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", ctypes.c_uint),
        ("dwStateMask", ctypes.c_uint),
        ("szInfo", ctypes.c_wchar * 256),
        ("uTimeoutOrVersion", ctypes.c_uint),
        ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", ctypes.c_uint),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", wintypes.HWND),
    ]


# 窗口过程回调类型
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, ctypes.c_uint,
                              wintypes.WPARAM, wintypes.LPARAM)


class SystemTrayIcon:
    """Windows 系统托盘图标"""

    def __init__(self, tooltip="Quick Translate", on_toggle=None, on_exit=None):
        self.tooltip = tooltip
        self.on_toggle = on_toggle
        self.on_exit = on_exit
        self._nid = None
        self._hwnd = None
        self._thread = None
        self._running = False
        self._wndproc_ref = None  # 防止 GC

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._hwnd:
            if self._nid:
                shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
            user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)

    def _run(self):
        class_name = "QuickTranslateTrayClass"

        # 窗口过程
        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == WM_TRAYICON:
                if lparam == WM_LBUTTONUP:
                    if self.on_toggle:
                        self.on_toggle()
                elif lparam == WM_RBUTTONUP:
                    self._show_menu(hwnd)
                return 0
            elif msg == WM_COMMAND:
                cmd = wparam & 0xFFFF
                if cmd == 1001:
                    if self.on_toggle:
                        self.on_toggle()
                elif cmd == 1002:
                    if self.on_exit:
                        self.on_exit()
                    else:
                        self.stop()
                return 0
            elif msg == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
            # 显式转换参数类型，避免 64 位溢出
            return user32.DefWindowProcW(
                wintypes.HWND(hwnd),
                wintypes.UINT(msg),
                wintypes.WPARAM(wparam),
                wintypes.LPARAM(lparam))

        self._wndproc_ref = WNDPROC(wnd_proc)

        # 注册窗口类
        wc = WNDCLASSEX()
        wc.cbSize = ctypes.sizeof(WNDCLASSEX)
        wc.style = CS_HREDRAW | CS_VREDRAW
        wc.lpfnWndProc = ctypes.cast(self._wndproc_ref, ctypes.c_void_p)
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.lpszClassName = class_name

        atom = user32.RegisterClassExW(ctypes.byref(wc))
        if not atom:
            print("[Tray] Failed to register window class")
            self._running = False
            return

        # 创建隐藏窗口
        self._hwnd = user32.CreateWindowExW(
            0, class_name, "QuickTranslateTray", 0,
            0, 0, 0, 0, 0, 0, wc.hInstance, None
        )
        if not self._hwnd:
            print("[Tray] Failed to create hidden window")
            self._running = False
            return

        # 加载图标
        hicon = user32.LoadIconW(0, IDI_APPLICATION)

        # 创建托盘图标
        self._nid = NOTIFYICONDATA()
        self._nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        self._nid.hWnd = self._hwnd
        self._nid.uID = 1
        self._nid.uFlags = NIF_ICON | NIF_TIP | NIF_MESSAGE
        self._nid.uCallbackMessage = WM_TRAYICON
        self._nid.hIcon = hicon
        self._nid.szTip = self.tooltip

        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self._nid))
        print("[Tray] Icon added")

        # 消息循环
        msg = wintypes.MSG()
        while self._running:
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret == 0 or ret == -1:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        print("[Tray] Stopped")

    def _show_menu(self, hwnd):
        """显示右键菜单"""
        menu = user32.CreatePopupMenu()
        user32.AppendMenuW(menu, 0, 1001, "显示/隐藏 Quick Translate")
        user32.AppendMenuW(menu, 0x00000800, 0, None)  # 分隔线
        user32.AppendMenuW(menu, 0, 1002, "退出")

        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(hwnd)
        user32.TrackPopupMenu(menu, 0x0100, pt.x, pt.y, 0, hwnd, None)
        user32.PostMessageW(hwnd, 0, 0, 0)
        user32.DestroyMenu(menu)
