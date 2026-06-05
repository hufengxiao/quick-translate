"""Spotlight-style UI — Apple HIG design, smooth animations, modern layout."""
from __future__ import annotations
import ctypes
import tkinter as tk
from tkinter import font as tkfont
import traceback
from typing import Optional, Callable, List, Dict

from .theme import Theme, DARK, get_theme
from .animator import Animator
from .layout import Spacing, Sizes, Fonts
from ..utils.logging import logger


class SpotlightUI:
    """Apple Spotlight-inspired translation window."""

    def __init__(self, config, on_search: Callable, on_translate: Callable,
                 history=None):
        self.cfg = config
        self.theme = get_theme("dark")
        self.t = self.theme  # shorthand
        self.on_search = on_search
        self.on_translate = on_translate
        self.history = history
        self.opacity = config.ui.opacity
        self._visible = False
        self._selected_idx = -1
        self._matches: List[Dict[str, str]] = []
        self._settings_win = None
        self._toast_after = None
        self._ai_pending_query = None

        self._build_window()
        self._build_widgets()
        self._animator = Animator(self.root)

    # ── Window Setup ──

    def _build_window(self):
        self.root = tk.Tk()
        self.root.title("Quick Translate")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.0)  # Start transparent for fade-in animation
        self.root.configure(bg=self.t.bg)

        w, h = Sizes.WINDOW_WIDTH, Sizes.WINDOW_HEIGHT
        pos = self.cfg.window_position
        if pos and "x" in pos and "y" in pos:
            x, y = pos["x"], pos["y"]
        else:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = (sw - w) // 2
            y = (sh - h) // 3
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        # Windows 11 rounded corners
        self._apply_rounded_corners(self.root)

        self.root.bind("<Escape>", lambda e: self.hide())
        self.root.bind("<FocusIn>", self._on_focus_in)
        self.root.bind("<FocusOut>", self._on_focus_out)

        self._drag_x = 0
        self._drag_y = 0

    def _apply_rounded_corners(self, window):
        """Apply Windows 11 DWM rounded corners."""
        try:
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            pref = ctypes.c_int(2)  # DWMWCP_ROUND
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, ctypes.byref(pref), ctypes.sizeof(pref))
        except Exception:
            pass  # Windows 10 or older — gracefully skip

    # ── Drag ──

    def _bind_drag(self, widget):
        widget.bind("<Button-1>", self._on_drag_start, add="+")
        widget.bind("<B1-Motion>", self._on_drag_motion, add="+")

    def _on_drag_start(self, event):
        self._drag_x = self.root.winfo_pointerx()
        self._drag_y = self.root.winfo_pointery()
        self._win_x = self.root.winfo_x()
        self._win_y = self.root.winfo_y()

    def _on_drag_motion(self, event):
        dx = self.root.winfo_pointerx() - self._drag_x
        dy = self.root.winfo_pointery() - self._drag_y
        self.root.geometry(f"+{self._win_x + dx}+{self._win_y + dy}")

    # ── Focus ──

    def _on_focus_in(self, event):
        self.root.attributes("-alpha", self.opacity)

    def _on_focus_out(self, event):
        if self._settings_win is None:
            self.root.attributes("-alpha", 0.08)

    # ── Icon Buttons ──

    def _make_icon_btn(self, parent, text, command=None):
        btn = tk.Label(
            parent, text=text, bg=self.t.surface, fg=self.t.fg_tertiary,
            font=(Fonts.FAMILY_FALLBACK, 11), cursor="hand2",
            padx=Spacing.SM, pady=Spacing.XS,
        )

        def on_enter(e):
            btn.config(fg=self.t.fg, bg=self.t.surface2)

        def on_leave(e):
            btn.config(fg=self.t.fg_tertiary, bg=self.t.surface)

        def on_press(e):
            btn.config(fg=self.t.accent, bg=self.t.surface2)

        def on_release(e):
            btn.config(fg=self.t.fg, bg=self.t.surface2)
            if command:
                command()

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        btn.bind("<ButtonPress-1>", on_press)
        btn.bind("<ButtonRelease-1>", on_release)
        return btn

    # ── Settings Popup ──

    def _open_settings(self):
        if self._settings_win is not None:
            self._settings_win.destroy()
            self._settings_win = None
            return

        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", self.opacity)
        win.configure(bg=self.t.surface)
        self._settings_win = win
        self._apply_rounded_corners(win)

        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        win.geometry(f"220x80+{rx + rw - 220}+{ry + Spacing.SM}")

        tk.Label(
            win, text="透明度", font=(Fonts.FAMILY_FALLBACK, Fonts.SIZE_CAPTION),
            bg=self.t.surface, fg=self.t.fg,
        ).pack(pady=(Spacing.SM, 0))

        var = tk.DoubleVar(value=self.opacity)

        def on_slider(v):
            self._set_opacity(float(v))
            win.attributes("-alpha", float(v))

        tk.Scale(
            win, from_=0.1, to=0.9, resolution=0.1,
            orient=tk.HORIZONTAL, variable=var, command=on_slider,
            bg=self.t.surface, fg=self.t.fg,
            highlightthickness=0, troughcolor=self.t.bg,
            sliderrelief=tk.FLAT, length=190, showvalue=True,
            bd=0, font=(Fonts.FAMILY_FALLBACK, 8),
        ).pack(padx=Spacing.SM, pady=(0, Spacing.SM))

        def close_settings(e=None):
            if self._settings_win:
                self._settings_win.destroy()
                self._settings_win = None

        win.bind("<FocusOut>", close_settings)
        win.focus_set()

    def _set_opacity(self, value):
        self.opacity = value
        self.root.attributes("-alpha", self.opacity)

    # ── Toast ──

    def _show_toast(self, text, duration=2000):
        if self._toast_after:
            self.root.after_cancel(self._toast_after)
            if hasattr(self, '_toast_label') and self._toast_label:
                try:
                    self._toast_label.destroy()
                except Exception:
                    pass

        self._toast_label = tk.Label(
            self.root, text=text,
            font=(Fonts.FAMILY_FALLBACK, Fonts.SIZE_CAPTION),
            bg=self.t.toast_bg, fg=self.t.toast_fg,
            padx=Spacing.MD, pady=Spacing.XS,
        )
        self._toast_label.place(relx=0.5, rely=0.95, anchor="s")
        self._toast_after = self.root.after(
            duration, lambda: self._toast_label.destroy()
            if hasattr(self, '_toast_label') and self._toast_label else None)

    # ── Build Widgets ──

    def _build_widgets(self):
        t = self.t
        S = Spacing

        default_font = tkfont.Font(family=Fonts.FAMILY_FALLBACK, size=Fonts.SIZE_BODY)
        small_font = tkfont.Font(family=Fonts.FAMILY_FALLBACK, size=Fonts.SIZE_CAPTION)
        bold_font = tkfont.Font(family=Fonts.FAMILY_FALLBACK, size=Fonts.SIZE_BODY, weight="bold")
        mono_font = tkfont.Font(family=Fonts.FAMILY_MONO_FALLBACK, size=10)

        main = tk.Frame(self.root, bg=t.bg)
        main.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self._bind_drag(main)

        # ── Top Bar ──
        top_bar = tk.Frame(main, bg=t.bg, height=Sizes.TOP_BAR_HEIGHT)
        top_bar.pack(fill=tk.X, padx=S.LG, pady=(S.SM, 0))
        top_bar.pack_propagate(False)
        self._bind_drag(top_bar)

        close_btn = self._make_icon_btn(top_bar, "✕", command=self.hide)
        close_btn.pack(side=tk.RIGHT, padx=(S.XS, S.SM))

        settings_btn = self._make_icon_btn(top_bar, "⚙", command=self._open_settings)
        settings_btn.pack(side=tk.RIGHT, padx=(0, S.XS))

        # ── Search Bar ──
        search_frame = tk.Frame(main, bg=t.entry_bg, height=Sizes.SEARCH_HEIGHT)
        search_frame.pack(fill=tk.X, padx=S.LG, pady=(S.SM, S.SM))
        search_frame.pack_propagate(False)
        self._bind_drag(search_frame)

        icon_label = tk.Label(
            search_frame, text="🔍", bg=t.entry_bg, fg=t.fg,
            font=("Segoe UI Emoji", 12),
        )
        icon_label.pack(side=tk.LEFT, padx=(S.SM, S.XS))
        self._bind_drag(icon_label)

        self.entry = tk.Entry(
            search_frame, font=default_font,
            bg=t.entry_bg, fg=t.entry_fg,
            insertbackground=t.accent,
            relief=tk.FLAT, highlightthickness=0,
        )
        self.entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, S.XS), pady=S.SM)

        # Clear button
        self._clear_btn = tk.Label(
            search_frame, text="✕", bg=t.entry_bg, fg=t.fg_tertiary,
            font=(Fonts.FAMILY_FALLBACK, 9), cursor="hand2", padx=S.SM,
        )
        self._clear_btn.bind("<Button-1>", lambda e: self._clear_input())
        self._clear_btn.bind("<Enter>", lambda e: self._clear_btn.config(fg=t.fg))
        self._clear_btn.bind("<Leave>", lambda e: self._clear_btn.config(fg=t.fg_tertiary))

        self.entry.bind("<Key>", self._on_key)
        self.entry.bind("<Down>", self._on_arrow_down)
        self.entry.bind("<Up>", self._on_arrow_up)
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<Tab>", self._on_tab)

        # ── Candidate List ──
        list_frame = tk.Frame(main, bg=t.list_bg)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=S.LG, pady=(0, S.XS))

        self.listbox = tk.Listbox(
            list_frame, font=mono_font,
            bg=t.list_bg, fg=t.fg,
            selectbackground=t.list_selected_bg,
            selectforeground=t.list_selected_fg,
            relief=tk.FLAT, highlightthickness=0,
            activestyle="none",
            bd=0,
        )
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<MouseWheel>",
                          lambda e: self.listbox.yview_scroll(-e.delta // 120, "units"))
        self.listbox.bind("<<ListboxSelect>>", self._on_list_select)
        self.listbox.bind("<Double-Button-1>", self._on_double_click)

        # ── Definition Panel ──
        def_frame = tk.Frame(main, bg=t.bg)
        def_frame.pack(fill=tk.BOTH, expand=True, padx=S.LG, pady=(S.XS, S.LG))
        self._bind_drag(def_frame)

        self.def_title = tk.Label(
            def_frame, text="输入单词开始查询…", font=bold_font,
            bg=t.bg, fg=t.accent, anchor="w",
        )
        self.def_title.pack(fill=tk.X, pady=(0, S.XS))
        self._bind_drag(self.def_title)

        self.def_text = tk.Text(
            def_frame, font=small_font,
            bg=t.bg, fg=t.fg,
            relief=tk.FLAT, highlightthickness=0,
            wrap=tk.WORD, state=tk.DISABLED, cursor="arrow",
            bd=0, padx=0, pady=0,
        )
        self.def_text.pack(fill=tk.BOTH, expand=True)
        self.def_text.bind("<Button-1>", self._on_copy_definition)

        # Welcome toast
        self.root.after(500, lambda: self._show_toast(
            "Shift+Ctrl+M 唤出  |  ↑↓选择  |  Enter AI翻译", 4000))

    # ── Clear ──

    def _clear_input(self):
        self.entry.delete(0, tk.END)
        self._clear_matches()
        self.entry.focus_set()
        self._clear_btn.pack_forget()

    # ── Search Logic ──

    def _on_key(self, event):
        if event.keysym in ("Down", "Up", "Return", "Tab", "Escape",
                             "Shift_L", "Shift_R", "Control_L", "Control_R",
                             "Alt_L", "Alt_R"):
            return
        self.root.after(1, self._do_search)

    def _do_search(self):
        query = self.entry.get().strip()

        if query:
            self._clear_btn.pack(side=tk.RIGHT, padx=(0, Spacing.SM))
        else:
            self._clear_btn.pack_forget()

        if not query:
            self._clear_matches()
            return

        try:
            self._matches = self.on_search(query)
            self._update_listbox(query)
        except Exception as e:
            self._set_definition("搜索出错", str(e))
            traceback.print_exc()

    def _update_listbox(self, query: str = ""):
        self.listbox.delete(0, tk.END)
        self._selected_idx = -1
        self._ai_pending_query = None

        if not self._matches:
            self.listbox.insert(tk.END, "  🤖 本地无结果，按 Enter AI 翻译")
            self._ai_pending_query = query
            self._set_definition("未找到本地释义", f'按 Enter 使用 AI 翻译 "{query}"')
            return

        for m in self._matches:
            word = m["word"]
            defn = m.get("definition", "").split("\n")[0]
            if len(defn) > 22:
                defn = defn[:22] + "…"
            self.listbox.insert(tk.END, f"  {word}  {defn}")

        # Auto-select first
        self.listbox.selection_set(0)
        self.listbox.activate(0)
        self._selected_idx = 0
        self._show_definition(0, record_history=False)

    def _clear_matches(self):
        self._matches = []
        self._ai_pending_query = None
        self.listbox.delete(0, tk.END)
        if self.history:
            recent = self.history.get_recent(8)
            if recent:
                for h in recent:
                    word = h.get("word", "")
                    defn = h.get("definition", "")
                    time_str = h.get("time", "")
                    if len(defn) > 18:
                        defn = defn[:18] + "…"
                    self.listbox.insert(tk.END, f"  🕐 {word}  {defn}  {time_str}")
                self._set_definition("最近查词", "输入新的单词开始查询，或从历史中选择")
                return
        self._set_definition("输入单词开始查询…", "")

    # ── Keyboard Navigation ──

    def _on_arrow_down(self, event):
        if self._matches:
            self._selected_idx = min(self._selected_idx + 1, len(self._matches) - 1)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self._selected_idx)
            self.listbox.see(self._selected_idx)
            self._show_definition(self._selected_idx)
        return "break"

    def _on_arrow_up(self, event):
        if self._matches:
            self._selected_idx = max(self._selected_idx - 1, 0)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self._selected_idx)
            self.listbox.see(self._selected_idx)
            self._show_definition(self._selected_idx)
        return "break"

    def _on_enter(self, event):
        if self._ai_pending_query:
            self._trigger_ai(self._ai_pending_query)
            return "break"
        if 0 <= self._selected_idx < len(self._matches):
            word = self._matches[self._selected_idx]["word"]
            self._trigger_ai(word)
        return "break"

    def _on_tab(self, event):
        query = self.entry.get().strip()
        if query:
            self._trigger_ai(query)
        return "break"

    def _trigger_ai(self, query: str):
        self._set_definition("🤖 AI 翻译中…", f'正在翻译 "{query}"，请稍候…')
        self.on_translate(query, self._on_ai_result, self._on_ai_error)

    def _on_ai_result(self, text: str):
        self.root.after(0, lambda: self._set_definition("🤖 AI 翻译结果", text))

    def _on_ai_error(self, error: str):
        self.root.after(0, lambda: self._set_definition("翻译失败", f"错误: {error}"))

    # ── List Interaction ──

    def _on_list_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if self._matches and idx < len(self._matches):
            self._selected_idx = idx
            self._show_definition(idx)
        elif self.history:
            recent = self.history.get_recent(8)
            if idx < len(recent):
                word = recent[idx].get("word", "")
                if word:
                    self.entry.delete(0, tk.END)
                    self.entry.insert(0, word)
                    self._do_search()

    def _on_double_click(self, event):
        sel = self.listbox.curselection()
        if sel and self._matches:
            idx = sel[0]
            if idx < len(self._matches):
                word = self._matches[idx]["word"]
                self._trigger_ai(word)

    # ── Definition Display ──

    def _show_definition(self, idx: int, record_history=True):
        if 0 <= idx < len(self._matches):
            m = self._matches[idx]
            word = m["word"]
            defn = m.get("definition", "无释义")
            self._set_definition(word, defn)
            if record_history and self.history:
                self.history.add(word, defn)

    def _set_definition(self, title: str, content: str):
        self.def_title.config(text=title)
        self.def_text.config(state=tk.NORMAL)
        self.def_text.delete("1.0", tk.END)
        if content:
            self.def_text.insert("1.0", content)
        self.def_text.config(state=tk.DISABLED)

    # ── Copy Definition ──

    def _on_copy_definition(self, event=None):
        title = self.def_title.cget("text")
        skip_titles = ("输入单词开始查询…", "最近查词", "搜索出错",
                        "翻译失败", "AI 翻译中…", "未找到本地释义")
        if title in skip_titles or title.startswith("🤖"):
            return
        content = self.def_text.get("1.0", tk.END).strip()
        if content and not content.startswith("输入新的单词"):
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self._show_toast("已复制到剪贴板 ✓", 1500)

    # ── Window Show/Hide with Animation ──

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.entry.focus_set()
        self.entry.select_range(0, tk.END)
        self._visible = True

        if not self.entry.get().strip():
            self._clear_matches()

        # Fade-in animation
        if self.cfg.ui.animations_enabled:
            self._animator.fade_in("show", target_alpha=self.opacity, duration_ms=200)
        else:
            self.root.attributes("-alpha", self.opacity)

    def _save_position(self):
        if not hasattr(self.cfg, 'window_position') or self.cfg.window_position is None:
            self.cfg.window_position = {}
        self.cfg.window_position["x"] = self.root.winfo_x()
        self.cfg.window_position["y"] = self.root.winfo_y()

    def hide(self):
        self._save_position()
        if self.cfg.ui.animations_enabled:
            def do_withdraw():
                self.root.withdraw()
                self._visible = False
            self._animator.fade_out("hide", duration_ms=150, on_complete=do_withdraw)
        else:
            self.root.withdraw()
            self._visible = False

        if self._settings_win:
            self._settings_win.destroy()
            self._settings_win = None

    def toggle(self):
        if self._visible:
            self.hide()
        else:
            self.show()

    def run(self):
        self.root.withdraw()
        self.root.mainloop()
