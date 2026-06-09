"""
Quick Translate 动画引擎
支持淡入、缩放、滑入等窗口动画
"""
import tkinter as tk
import math
from typing import Callable, Optional


class Easing:
    """缓动函数"""

    @staticmethod
    def ease_out(t: float) -> float:
        """减速缓出"""
        return 1 - (1 - t) ** 3

    @staticmethod
    def ease_in_out(t: float) -> float:
        """先加速后减速"""
        return 3 * t * t - 2 * t * t * t

    @staticmethod
    def spring(t: float) -> float:
        """弹性效果"""
        return 1 - math.cos(t * math.pi * 0.5) ** 3


class AnimationEngine:
    """动画引擎"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self._running = False

    def fade_in(self, widget: tk.Tk, duration: int = 200,
                from_alpha: float = 0.0, to_alpha: float = 1.0,
                on_complete: Optional[Callable] = None):
        """淡入动画"""
        steps = max(10, duration // 16)
        step_time = duration // steps
        delta = (to_alpha - from_alpha) / steps
        current_step = [0]

        def animate():
            current_step[0] += 1
            if current_step[0] > steps:
                widget.attributes("-alpha", to_alpha)
                if on_complete:
                    on_complete()
                return
            t = current_step[0] / steps
            alpha = from_alpha + delta * current_step[0]
            alpha = max(0.0, min(1.0, alpha))
            widget.attributes("-alpha", alpha)
            widget.after(step_time, animate)

        widget.attributes("-alpha", from_alpha)
        animate()

    def fade_out(self, widget: tk.Tk, duration: int = 150,
                 from_alpha: float = 1.0, to_alpha: float = 0.0,
                 on_complete: Optional[Callable] = None):
        """淡出动画"""
        self.fade_in(widget, duration, from_alpha, to_alpha, on_complete)

    def slide_in_from_top(self, widget: tk.Tk, target_y: int,
                           duration: int = 200, offset: int = -20,
                           on_complete: Optional[Callable] = None):
        """从上方滑入"""
        steps = max(10, duration // 16)
        step_time = duration // steps
        start_y = target_y + offset
        current_step = [0]

        def animate():
            current_step[0] += 1
            if current_step[0] > steps:
                # 确保精确到达目标位置
                geo = widget.geometry()
                parts = geo.split('+')
                if len(parts) >= 3:
                    widget.geometry(f"+{parts[1]}+{target_y}")
                if on_complete:
                    on_complete()
                return
            t = current_step[0] / steps
            eased_t = Easing.ease_out(t)
            y = int(start_y + (target_y - start_y) * eased_t)
            geo = widget.geometry()
            parts = geo.split('+')
            if len(parts) >= 3:
                widget.geometry(f"+{parts[1]}+{y}")
            widget.after(step_time, animate)

        geo = widget.geometry()
        parts = geo.split('+')
        if len(parts) >= 3:
            widget.geometry(f"+{parts[1]}+{start_y}")
        animate()

    def scale_appear(self, widget: tk.Tk, duration: int = 200,
                      on_complete: Optional[Callable] = None):
        """缩放出现效果（通过透明度模拟）"""
        self.fade_in(widget, duration, 0.0, 1.0, on_complete)

    def pulse(self, widget: tk.Widget, color_from: str, color_to: str,
              duration: int = 1000, cycles: int = 0):
        """脉冲动画（用于加载指示器）"""
        steps = max(20, duration // 16)
        step_time = duration // steps
        current_step = [0]
        count = [0]

        def hex_to_rgb(h):
            h = h.lstrip('#')
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        def rgb_to_hex(r, g, b):
            return f'#{int(r):02x}{int(g):02x}{int(b):02x}'

        r1, g1, b1 = hex_to_rgb(color_from)
        r2, g2, b2 = hex_to_rgb(color_to)

        def animate():
            current_step[0] += 1
            if current_step[0] > steps:
                current_step[0] = 0
                count[0] += 1
                if cycles > 0 and count[0] >= cycles:
                    widget.config(fg=color_from)
                    return

            t = current_step[0] / steps
            # 正弦波
            factor = (math.sin(t * 2 * math.pi) + 1) / 2
            r = r1 + (r2 - r1) * factor
            g = g1 + (g2 - g1) * factor
            b = b1 + (b2 - b1) * factor
            try:
                widget.config(fg=rgb_to_hex(r, g, b))
            except tk.TclError:
                return
            widget.after(step_time, animate)

        animate()
