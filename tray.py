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
NIF_INFO = 0x00000010
WM_USER = 0x0400
WM_TRAYICON = WM_USER + 1
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
IDI_APPLICATION = 32512
LR_LOADFROMFILE = 0x00000010
LR_DEFAULTSIZE = 0x00000040

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32


class NOTIFYICONDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("hWnd", wintypes.HWND),
        ("uID", ctypes.c_uint),
        ("uFlags", ctypes.c_uint),
        ("uCallbackMessage", ctypes.c_uint),
        ("hIcon", wintypes.HICON),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", ctypes.c_uint),
        ("dwStateMask", ctypes.c_uint),
        ("szInfo", ctypes.c_wchar * 256),
        ("uTimeoutOrVersion", ctypes.c_uint),
        ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", ctypes.c_uint),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", wintypes.HICON),
    ]


class SystemTrayIcon:
    """Windows 系统托盘图标"""

    def __init__(self, tooltip="Quick Translate", on_toggle=None, on_exit=None):
        self.tooltip = tooltip
        self.on_toggle = on_toggle
        self.on_exit = on_exit
        self._nid = None
        self._hwnd = None
        self._menu_hwnd = None
        self._thread = None
        self._running = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._hwnd:
            # Remove tray icon
            if self._nid:
                shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
            user32.PostMessageW(self._hwnd, 0x0010, 0, 0)  # WM_CLOSE

    def _run(self):
        """在独立线程中创建隐藏窗口和托盘图标"""

        # Window procedure
        wndproc = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, ctypes.c_uint,
                                      wintypes.WPARAM, wintypes.LPARAM)

        def _wnd_proc(hwnd, msg, wparam, lparam):
            if msg == WM_TRAYICON:
                if lparam == WM_LBUTTONUP:
                    # 左键点击 → 切换窗口
                    if self.on_toggle:
                        self.on_toggle()
                elif lparam == WM_RBUTTONUP:
                    # 右键点击 → 显示菜单
                    self._show_menu(hwnd)
                return 0
            elif msg == 0x0102:  # WM_COMMAND
                cmd = wparam & 0xFFFF
                if cmd == 1001:  # Show/Hide
                    if self.on_toggle:
                        self.on_toggle()
                elif cmd == 1002:  # Exit
                    if self.on_exit:
                        self.on_exit()
                    else:
                        self.stop()
                return 0
            elif msg == 0x0002:  # WM_DESTROY
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wndproc = wndproc  # prevent GC

        # Register window class
        class_name = "QuickTranslateTray"

        wc = wintypes.WNDCLASSEX()
        wc.cbSize = ctypes.sizeof(wintypes.WNDCLASSEX)
        wc.lpfnWndProc = self._wndproc
        wc.hInstance = ctypes.windll.kernel32.GetModuleHandleW(None)
        wc.lpszClassName = class_name
        user32.RegisterClassExW(ctypes.byref(wc))

        # Create hidden window
        self._hwnd = user32.CreateWindowExW(
            0, class_name, "QuickTranslateTray", 0,
            0, 0, 0, 0, 0, 0, wc.hInstance, None
        )

        if not self._hwnd:
            print("[Tray] Failed to create window")
            self._running = False
            return

        # Load default application icon
        hicon = user32.LoadIconW(0, IDI_APPLICATION)

        # Create tray icon
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

        # Message loop
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

        # "显示/隐藏 Quick Translate"
        show_text = "显示/隐藏 Quick Translate"
        user32.AppendMenuW(menu, 0, 1001, show_text)
        user32.AppendMenuMenu = menu

        # 分隔线
        user32.AppendMenuW(menu, 0x00000800, 0, None)  # MF_SEPARATOR

        # "退出"
        user32.AppendMenuW(menu, 0, 1002, "退出")

        # 获取光标位置
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))

        # 设置前台窗口（必须，否则菜单不会自动消失）
        user32.SetForegroundWindow(hwnd)

        # 显示菜单
        user32.TrackPopupMenu(
            menu, 0x0100,  # TPM_RIGHTBUTTON
            pt.x, pt.y, 0, hwnd, None
        )

        # 发送空消息让菜单消失
        user32.PostMessageW(hwnd, 0, 0, 0)

        # 销毁菜单
        user32.DestroyMenu(menu)
