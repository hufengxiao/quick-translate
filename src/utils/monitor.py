"""Multi-monitor utilities — enumerate monitors, validate window positions."""
import ctypes
import ctypes.wintypes as wintypes
from typing import List, Tuple


# Windows API structures for monitor enumeration
class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


MONITOR_DEFAULTTONEAREST = 2
MONITORINFOF_PRIMARY = 1


def _enum_monitors() -> List[wintypes.RECT]:
    """Return list of (left, top, right, bottom) rectangles for all monitors."""
    rects: List[wintypes.RECT] = []

    def callback(hmon, hdc, lprect, lparam):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
        rects.append(mi.rcMonitor)
        return 1

    MONITORENUMPROC = ctypes.WINFUNCTYPE(
        ctypes.c_int, wintypes.HMONITOR, wintypes.HDC,
        ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
    )
    ctypes.windll.user32.EnumDisplayMonitors(
        None, None, MONITORENUMPROC(callback), 0
    )
    return rects


def get_monitor_rects() -> List[Tuple[int, int, int, int]]:
    """Return list of (left, top, right, bottom) for all monitors.

    Falls back to a single-screen estimate if the API call fails.
    """
    try:
        rects = _enum_monitors()
        if rects:
            return [(r.left, r.top, r.right, r.bottom) for r in rects]
    except Exception:
        pass
    # Fallback: assume one screen
    try:
        sw = ctypes.windll.user32.GetSystemMetrics(0)
        sh = ctypes.windll.user32.GetSystemMetrics(1)
        return [(0, 0, sw, sh)]
    except Exception:
        return [(0, 0, 1920, 1080)]


def point_on_monitor(x: int, y: int,
                     rects: List[Tuple[int, int, int, int]] = None) -> bool:
    """Check if point (x, y) falls inside any monitor rectangle."""
    if rects is None:
        rects = get_monitor_rects()
    for l, t, r, b in rects:
        if l <= x < r and t <= y < b:
            return True
    return False


def window_visible_on_monitor(x: int, y: int, w: int, h: int,
                              rects: List[Tuple[int, int, int, int]] = None,
                              min_visible: int = 50) -> bool:
    """Check if at least *min_visible* pixels of the window are on a monitor."""
    if rects is None:
        rects = get_monitor_rects()
    for l, t, r, b in rects:
        # Overlap area
        ox = max(0, min(x + w, r) - max(x, l))
        oy = max(0, min(y + h, b) - max(y, t))
        if ox >= min_visible and oy >= min_visible:
            return True
    return False


def clamp_position(x: int, y: int, w: int, h: int,
                   rects: List[Tuple[int, int, int, int]] = None) -> Tuple[int, int]:
    """If the window isn't well-visible on any monitor, reposition it.

    Returns (x, y) that ensures the window is visible.
    Strategy: find the monitor whose center is closest to the window center,
    and place the window centered on that monitor (upper-third).
    """
    if rects is None:
        rects = get_monitor_rects()

    if window_visible_on_monitor(x, y, w, h, rects, min_visible=50):
        return x, y

    # Find primary monitor (usually the one starting at 0,0) or largest
    primary = rects[0]
    for r in rects:
        if r[0] == 0 and r[1] == 0:
            primary = r
            break

    # Center on primary, upper-third
    pl, pt, pr, pb = primary
    new_x = pl + (pr - pl - w) // 2
    new_y = pt + (pb - pt - h) // 3
    return new_x, new_y
