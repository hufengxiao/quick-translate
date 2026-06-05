"""Animator — tkinter-compatible animation engine.

Provides smooth transitions for window show/hide, opacity, and element movement.
Uses root.after() for frame scheduling — no external dependencies.
"""
from __future__ import annotations
import math
import tkinter as tk
from typing import Callable, Optional


def ease_out_cubic(t: float) -> float:
    """Cubic ease-out — fast start, gentle deceleration."""
    return 1 - (1 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    """Cubic ease-in-out — smooth acceleration and deceleration."""
    if t < 0.5:
        return 4 * t * t * t
    return 1 - (-2 * t + 2) ** 3 / 2


def elastic_out(t: float) -> float:
    """Elastic ease-out — slight overshoot (Apple-style bounce)."""
    if t == 0 or t == 1:
        return t
    p = 0.3
    s = p / 4
    return math.pow(2, -10 * t) * math.sin((t - s) * (2 * math.pi) / p) + 1


def linear(t: float) -> float:
    return t


class Animator:
    """Animation controller for a tkinter root window."""

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._running: dict[str, bool] = {}

    def animate(self, name: str, duration_ms: int,
                on_frame: Callable[[float], None],
                on_complete: Optional[Callable[[], None]] = None,
                easing: Callable[[float], float] = ease_out_cubic,
                fps: int = 60) -> None:
        """Run a named animation.
        
        Args:
            name: Unique animation identifier (cancels previous with same name)
            duration_ms: Total animation duration
            on_frame: Called each frame with progress t in [0, 1]
            on_complete: Called when animation finishes
            easing: Easing function (default: cubic ease-out)
            fps: Target frame rate (default: 60)
        """
        # Cancel previous animation with same name
        self._running[name] = False
        self._running[name] = True

        frame_interval = max(1, 1000 // fps)
        total_frames = max(1, duration_ms // frame_interval)
        frame_count = [0]

        def tick():
            if not self._running.get(name, False):
                return
            frame_count[0] += 1
            t = min(1.0, frame_count[0] / total_frames)
            eased_t = easing(t)

            try:
                on_frame(eased_t)
            except Exception:
                return

            if t < 1.0:
                self._root.after(frame_interval, tick)
            else:
                self._running[name] = False
                if on_complete:
                    on_complete()

        self._root.after(0, tick)

    def cancel(self, name: str) -> None:
        self._running[name] = False

    def cancel_all(self) -> None:
        self._running.clear()

    # ── Convenience methods ──

    def fade_in(self, name: str, target_alpha: float = 0.96,
                duration_ms: int = 200, on_complete: Optional[Callable] = None) -> None:
        """Fade window in from transparent to target_alpha."""
        start_alpha = 0.0
        def on_frame(t: float):
            alpha = start_alpha + (target_alpha - start_alpha) * t
            self._root.attributes("-alpha", alpha)
        self.animate(name, duration_ms, on_frame, on_complete, easing=elastic_out)

    def fade_out(self, name: str, duration_ms: int = 150,
                 on_complete: Optional[Callable] = None) -> None:
        """Fade window out to transparent."""
        try:
            start_alpha = self._root.attributes("-alpha")
        except Exception:
            start_alpha = 0.96
        def on_frame(t: float):
            alpha = start_alpha * (1 - t)
            self._root.attributes("-alpha", max(0, alpha))
        self.animate(name, duration_ms, on_frame, on_complete, easing=ease_out_cubic)

    def scale_window(self, name: str, start_w: int, start_h: int,
                     end_w: int, end_h: int, center_x: int, center_y: int,
                     duration_ms: int = 200, on_complete: Optional[Callable] = None) -> None:
        """Scale window from start size to end size, centered on (center_x, center_y)."""
        def on_frame(t: float):
            w = int(start_w + (end_w - start_w) * t)
            h = int(start_h + (end_h - start_h) * t)
            x = center_x - w // 2
            y = center_y - h // 2
            self._root.geometry(f"{w}x{h}+{x}+{y}")
        self.animate(name, duration_ms, on_frame, on_complete, easing=elastic_out)
