"""Windows 系统托盘图标 - 纯 ctypes 实现，零依赖"""
import ctypes
import ctypes.wintypes as wintypes
import threading
import os

# Windows constants
NIM_ADD = 0x00000000
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
WM_TRAYICON = 0x0400 + 1
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_COMMAND = 0x0111
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_QUIT = 0x0012
IDI_APPLICATION = 32512
LR_LOADFROMFILE = 0x00000010
IMAGE_ICON = 1

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32


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
        ("hIcon", wintypes.HANDLE),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", ctypes.c_uint),
        ("dwStateMask", ctypes.c_uint),
        ("szInfo", ctypes.c_wchar * 256),
        ("uTimeoutOrVersion", ctypes.c_uint),
        ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", ctypes.c_uint),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", wintypes.HANDLE),
    ]


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
        self._wndproc_ref = None

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
                self._nid = None
            user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)
            self._hwnd = None

    def _load_icon(self, hinstance):
        """加载 ICO 文件，失败则用默认图标"""
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "data", "icon.ico")
        if os.path.exists(icon_path):
            hicon = user32.LoadImageW(
                hinstance, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
            if hicon:
                return hicon
        return user32.LoadIconW(0, IDI_APPLICATION)

    def _run(self):
        class_name = "QuickTranslateTray"

        # 引用外部变量供回调使用
        outer = self

        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == WM_TRAYICON:
                if lparam == WM_LBUTTONUP:
                    if outer.on_toggle:
                        outer.on_toggle()
                elif lparam == WM_RBUTTONUP:
                    outer._show_menu(hwnd)
                return 0
            elif msg == WM_COMMAND:
                cmd_id = wparam & 0xFFFF
                if cmd_id == 1001:
                    if outer.on_toggle:
                        outer.on_toggle()
                elif cmd_id == 1002:
                    if outer.on_exit:
                        outer.on_exit()
                    else:
                        outer.stop()
                return 0
            elif msg == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(
                wintypes.HWND(hwnd),
                wintypes.UINT(msg),
                wintypes.WPARAM(wparam),
                wintypes.LPARAM(lparam))

        self._wndproc_ref = WNDPROC(wnd_proc)

        hinstance = kernel32.GetModuleHandleW(None)

        wc = WNDCLASSEX()
        wc.cbSize = ctypes.sizeof(WNDCLASSEX)
        wc.lpfnWndProc = ctypes.cast(self._wndproc_ref, ctypes.c_void_p)
        wc.hInstance = hinstance
        wc.lpszClassName = class_name

        atom = user32.RegisterClassExW(ctypes.byref(wc))
        if not atom:
            print("[Tray] Failed to register window class")
            self._running = False
            return

        # 用明确的类型参数创建窗口，避免 64 位溢出
        self._hwnd = user32.CreateWindowExW(
            wintypes.DWORD(0),       # dwExStyle
            class_name,              # lpClassName
            "QuickTranslateTray",    # lpWindowName
            wintypes.DWORD(0),       # dwStyle
            wintypes.INT(0),         # x
            wintypes.INT(0),         # y
            wintypes.INT(0),         # nWidth
            wintypes.INT(0),         # nHeight
            wintypes.HWND(0),        # hWndParent
            wintypes.HMENU(0),       # hMenu
            hinstance,               # hInstance
            None                     # lpParam
        )
        if not self._hwnd:
            print("[Tray] Failed to create hidden window")
            self._running = False
            return

        # 加载图标
        hicon = self._load_icon(hinstance)

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

        # 清理
        if self._nid:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
            self._nid = None
        print("[Tray] Stopped")

    def _show_menu(self, hwnd):
        menu = user32.CreatePopupMenu()
        user32.AppendMenuW(menu, 0, 1001, "显示/隐藏")
        user32.AppendMenuW(menu, 0x00000800, 0, None)
        user32.AppendMenuW(menu, 0, 1002, "退出")

        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(hwnd)
        user32.TrackPopupMenu(menu, 0x0100, pt.x, pt.y, 0, hwnd, None)
        user32.PostMessageW(hwnd, 0, 0, 0)
        user32.DestroyMenu(menu)
