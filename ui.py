"""主窗口 UI - Apple Spotlight 风格（使用设计系统）"""
import re
import tkinter as tk
from tkinter import font as tkfont
import ctypes
import traceback
from typing import Optional, Callable, List, Dict

from styles import StyleManager
from animations import AnimationEngine
from settings_panel import SettingsPanel

# POS tag extraction pattern (same as src/ui/spotlight.py)
_POS_PATTERN = re.compile(
    r'^(?:'
    r'(?:adj|adv|n|v|vt|vi|prep|conj|pron|det|art|aux|int|abbr|num|pl|sing)\.'
    r'(?:\s+(?:adj|adv|n|v|vt|vi|prep|conj|pron|det|art|aux|int|abbr|num|pl|sing)\.)*'
    r')',
    re.IGNORECASE,
)


def _extract_pos(text: str) -> str:
    """Extract part-of-speech tags from definition text.

    Returns a compact POS string like 'n.' or 'v. adj.' or '' if not found.
    """
    if not text:
        return ''
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        m = _POS_PATTERN.match(line)
        if m:
            raw = m.group(0)
            tags = re.findall(r'(adj|adv|n|v|vt|vi|prep|conj|pron|det|art|aux|int|abbr|num|pl|sing)\.',
                              raw, re.IGNORECASE)
            seen = set()
            unique_tags = []
            for t in tags:
                norm = t.lower() + '.'
                if norm not in seen:
                    seen.add(norm)
                    unique_tags.append(norm)
            if unique_tags:
                return ' '.join(unique_tags)
        # Check for Chinese POS patterns
        cn_pos_map = {'名词': 'n.', '动词': 'v.', '及物动词': 'vt.', '不及物动词': 'vi.',
                      '形容词': 'adj.', '副词': 'adv.', '介词': 'prep.', '连词': 'conj.',
                      '代词': 'pron.', '感叹词': 'int.', '数词': 'num.'}
        cn_tags = []
        for cn, en in cn_pos_map.items():
            if cn in line:
                cn_tags.append(en)
        if cn_tags:
            return ' '.join(cn_tags)
        break
    return ''


class SpotlightUI:
    """Spotlight 风格的查词窗口"""

    def __init__(self, config: dict,
                 on_search: Callable[[str], List[Dict[str, str]]],
                 on_translate: Callable[[str, Callable, Optional[Callable]], None],
                 history=None, vocabulary=None):
        self.cfg = config
        self.on_search = on_search
        self.on_translate = on_translate
        self.history = history
        self.vocabulary = vocabulary

        # 设计系统
        theme_name = config.get("ui", {}).get("theme", "dark")
        self.sm = StyleManager(theme_name)
        self.p = self.sm.palette

        self.opacity = config["ui"]["opacity"]
        self._visible = False
        self._selected_idx = -1
        self._matches: List[Dict[str, str]] = []
        self._settings_panel = None
        self._toast_after = None
        self._ai_pending_query = None
        self._detail_mode = False  # False=list mode, True=detail mode

        # System theme polling state
        self._config_theme = theme_name  # raw config value (may be "system")
        self._last_system_theme = self.sm.theme if theme_name == 'system' else None

        self._build_window()
        self._build_widgets()
        self.anim = AnimationEngine(self.root)

    def _build_window(self):
        self.root = tk.Tk()
        self.root.title("Quick Translate")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self.opacity)
        self.root.configure(bg=self.p.bg_primary)

        w = self.cfg["ui"]["width"]
        h = self.cfg["ui"]["height"]
        pos = self.cfg.get("window_position")
        if pos and "x" in pos and "y" in pos:
            x, y = pos["x"], pos["y"]
        else:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = (sw - w) // 2
            y = (sh - h) // 3
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        # DPI 感知
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

        # 圆角
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            pref = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, ctypes.byref(pref), ctypes.sizeof(pref))
        except Exception:
            pass

        self.root.bind("<Escape>", self._on_escape)
        self.root.bind("<FocusIn>", self._on_focus_in)
        self.root.bind("<FocusOut>", self._on_focus_out)
        self._drag_x = 0
        self._drag_y = 0

        # Resize state
        self._resize_zone = ''
        self._resize_start_x = 0
        self._resize_start_y = 0
        self._resize_start_w = 0
        self._resize_start_h = 0
        self._resize_start_win_x = 0
        self._resize_start_win_y = 0
        self._min_width = 280
        self._min_height = 300

    # ── 拖拽 ──

    def _bind_drag(self, widget):
        widget.bind("<Button-1>", self._on_drag_start, add="+")
        widget.bind("<B1-Motion>", self._on_drag_motion, add="+")

    def _on_drag_start(self, event):
        self._drag_x = self.root.winfo_pointerx()
        self._drag_y = self.root.winfo_pointery()
        self._win_x = self.root.winfo_x()
        self._win_y = self.root.winfo_y()

    def _on_drag_motion(self, event):
        if self._resize_zone:
            return  # Don't drag while resizing
        dx = self.root.winfo_pointerx() - self._drag_x
        dy = self.root.winfo_pointery() - self._drag_y
        self.root.geometry(f"+{self._win_x + dx}+{self._win_y + dy}")

    # ── 窗口大小调整 ──

    _RESIZE_BORDER = 6

    def _create_resize_handles(self, parent):
        """Create invisible resize handles at window edges and corners."""
        b = self._RESIZE_BORDER

        # Right edge
        right = tk.Frame(parent, cursor="sb_h_double_arrow",
                         bg=parent.cget("bg"))
        right.place(relx=1.0, rely=0, anchor="ne", width=b, relheight=1.0)
        right.bind("<Button-1>", lambda e: self._resize_start(e, "e"))
        right.bind("<B1-Motion>", lambda e: self._resize_motion(e, "e"))
        right.bind("<ButtonRelease-1>", self._resize_end)

        # Bottom edge
        bottom = tk.Frame(parent, cursor="sb_v_double_arrow",
                          bg=parent.cget("bg"))
        bottom.place(relx=0, rely=1.0, anchor="sw", relwidth=1.0, height=b)
        bottom.bind("<Button-1>", lambda e: self._resize_start(e, "s"))
        bottom.bind("<B1-Motion>", lambda e: self._resize_motion(e, "s"))
        bottom.bind("<ButtonRelease-1>", self._resize_end)

        # Left edge
        left = tk.Frame(parent, cursor="sb_h_double_arrow",
                        bg=parent.cget("bg"))
        left.place(relx=0, rely=0, anchor="nw", width=b, relheight=1.0)
        left.bind("<Button-1>", lambda e: self._resize_start(e, "w"))
        left.bind("<B1-Motion>", lambda e: self._resize_motion(e, "w"))
        left.bind("<ButtonRelease-1>", self._resize_end)

        # Top edge
        top = tk.Frame(parent, cursor="sb_v_double_arrow",
                       bg=parent.cget("bg"))
        top.place(relx=0, rely=0, anchor="nw", relwidth=1.0, height=b)
        top.bind("<Button-1>", lambda e: self._resize_start(e, "n"))
        top.bind("<B1-Motion>", lambda e: self._resize_motion(e, "n"))
        top.bind("<ButtonRelease-1>", self._resize_end)

        # Bottom-right corner
        se = tk.Frame(parent, cursor="sizing", bg=parent.cget("bg"))
        se.place(relx=1.0, rely=1.0, anchor="se", width=b * 2, height=b * 2)
        se.bind("<Button-1>", lambda e: self._resize_start(e, "se"))
        se.bind("<B1-Motion>", lambda e: self._resize_motion(e, "se"))
        se.bind("<ButtonRelease-1>", self._resize_end)

        # Bottom-left corner
        sw = tk.Frame(parent, cursor="sizing", bg=parent.cget("bg"))
        sw.place(relx=0, rely=1.0, anchor="sw", width=b * 2, height=b * 2)
        sw.bind("<Button-1>", lambda e: self._resize_start(e, "sw"))
        sw.bind("<B1-Motion>", lambda e: self._resize_motion(e, "sw"))
        sw.bind("<ButtonRelease-1>", self._resize_end)

        # Top-right corner
        ne = tk.Frame(parent, cursor="sizing", bg=parent.cget("bg"))
        ne.place(relx=1.0, rely=0, anchor="ne", width=b * 2, height=b * 2)
        ne.bind("<Button-1>", lambda e: self._resize_start(e, "ne"))
        ne.bind("<B1-Motion>", lambda e: self._resize_motion(e, "ne"))
        ne.bind("<ButtonRelease-1>", self._resize_end)

        # Top-left corner
        nw = tk.Frame(parent, cursor="sizing", bg=parent.cget("bg"))
        nw.place(relx=0, rely=0, anchor="nw", width=b * 2, height=b * 2)
        nw.bind("<Button-1>", lambda e: self._resize_start(e, "nw"))
        nw.bind("<B1-Motion>", lambda e: self._resize_motion(e, "nw"))
        nw.bind("<ButtonRelease-1>", self._resize_end)

    def _resize_start(self, event, zone):
        self._resize_zone = zone
        self._resize_start_x = event.x_root
        self._resize_start_y = event.y_root
        self._resize_start_w = self.root.winfo_width()
        self._resize_start_h = self.root.winfo_height()
        self._resize_start_win_x = self.root.winfo_x()
        self._resize_start_win_y = self.root.winfo_y()

    def _resize_motion(self, event, zone):
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y

        new_w = self._resize_start_w
        new_h = self._resize_start_h
        new_x = self._resize_start_win_x
        new_y = self._resize_start_win_y

        if 'e' in zone:
            new_w = max(self._min_width, self._resize_start_w + dx)
        if 'w' in zone:
            new_w = max(self._min_width, self._resize_start_w - dx)
            new_x = self._resize_start_win_x + (self._resize_start_w - new_w)
        if 's' in zone:
            new_h = max(self._min_height, self._resize_start_h + dy)
        if 'n' in zone:
            new_h = max(self._min_height, self._resize_start_h - dy)
            new_y = self._resize_start_win_y + (self._resize_start_h - new_h)

        self.root.geometry(
            f"{int(new_w)}x{int(new_h)}+{int(new_x)}+{int(new_y)}")

    def _resize_end(self, event=None):
        if not self._resize_zone:
            return
        self._resize_zone = ''
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        self.cfg["ui"]["width"] = w
        self.cfg["ui"]["height"] = h
        from config import save_config
        save_config(self.cfg)

    # ── 失焦/获焦 ──

    def _on_focus_in(self, event):
        self.root.attributes("-alpha", self.opacity)

    def _on_focus_out(self, event):
        panel_open = self._settings_panel is not None and self._settings_panel.is_open
        if not panel_open:
            self.root.attributes("-alpha", 0.1)

    # ── 按钮 ──

    def _make_icon_btn(self, parent, text, command=None):
        bg = self.p.bg_primary
        btn = tk.Label(parent, text=text, bg=bg, fg=self.p.text_tertiary,
                       font=("Segoe UI", 11), cursor="hand2", padx=4, pady=2)

        def on_enter(e):
            btn.config(fg=self.p.text_primary, bg=self.p.bg_tertiary)

        def on_leave(e):
            btn.config(fg=self.p.text_tertiary, bg=bg)

        def on_press(e):
            btn.config(fg=self.p.accent_primary, bg=self.p.bg_elevated)

        def on_release(e):
            btn.config(fg=self.p.text_primary, bg=self.p.bg_tertiary)
            if command:
                command()

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        btn.bind("<ButtonPress-1>", on_press)
        btn.bind("<ButtonRelease-1>", on_release)
        return btn

    # ── 设置弹窗 ──

    def _open_settings(self):
        if self._settings_panel is not None and self._settings_panel.is_open:
            self._settings_panel._close()
            self._settings_panel = None
            return

        def _on_save(new_cfg):
            """设置保存后回调"""
            from config import save_config
            self.cfg = new_cfg
            save_config(new_cfg)
            # 应用透明度
            self.opacity = new_cfg.get("ui", {}).get("opacity", 0.95)
            self.root.attributes("-alpha", self.opacity)
            self._show_toast("设置已保存 ✓", 1500)

        def _on_theme_change(theme_name):
            """主题预览"""
            self._apply_theme(theme_name)

        panel = SettingsPanel(
            parent=self.root,
            config=self.cfg,
            palette=self.p,
            style_manager=self.sm,
            on_save=_on_save,
            on_theme_change=_on_theme_change,
        )
        self._settings_panel = panel
        panel.show()

    def _set_opacity(self, value):
        self.opacity = value
        self.root.attributes("-alpha", self.opacity)

    def _apply_theme(self, theme_name: str):
        """Switch theme and rebuild the UI with new colors."""
        self._config_theme = theme_name  # track raw config value
        self.sm.set_theme(theme_name)
        self.p = self.sm.palette
        self.cfg["ui"]["theme"] = theme_name
        if theme_name == 'system':
            self._last_system_theme = self.sm.theme
        else:
            self._last_system_theme = None
        # Update root window background
        self.root.configure(bg=self.p.bg_primary)
        # Rebuild UI with new colors
        for widget in self.root.winfo_children():
            widget.destroy()
        self._build_widgets()
        self.anim = AnimationEngine(self.root)

    def _poll_system_theme(self):
        """Periodically check if the Windows system theme changed and auto-switch."""
        if self._config_theme == 'system':
            from system_theme import get_system_theme
            current = get_system_theme()
            if self._last_system_theme and current != self._last_system_theme:
                # System theme changed — switch without rebuilding settings
                self._last_system_theme = current
                self.sm.set_theme('system')  # re-resolves to new theme
                self.p = self.sm.palette
                self.root.configure(bg=self.p.bg_primary)
                for widget in self.root.winfo_children():
                    widget.destroy()
                self._build_widgets()
                self.anim = AnimationEngine(self.root)
        # Poll every 10 seconds
        self.root.after(10000, self._poll_system_theme)

    # ── 新用户引导 ──

    def _show_guide(self):
        """首次启动引导 toast 序列"""
        tips = [
            ("Shift+Ctrl+M 唤出窗口", 3000),
            ("输入英文查词，↑↓ 选择", 3000),
            ("Enter 查看详情 | Esc 返回", 3000),
            ("Tab AI翻译 | 点击释义复制", 3000),
        ]
        delay = 500
        for text, duration in tips:
            self.root.after(delay, lambda t=text, d=duration: self._show_toast(t, d))
            delay += duration + 200

    # ── Toast ──

    def _show_toast(self, text, duration=2000):
        if self._toast_after:
            self.root.after_cancel(self._toast_after)
            if hasattr(self, '_toast_label') and self._toast_label:
                self._toast_label.destroy()

        self._toast_label = tk.Label(
            self.root, text=text, font=("Segoe UI", 9),
            bg=self.p.bg_elevated, fg=self.p.text_primary, padx=10, pady=4,
        )
        self._toast_label.place(relx=0.5, rely=0.95, anchor="s")
        self._toast_after = self.root.after(
            duration, lambda: self._toast_label.destroy() if self._toast_label else None)

    # ── 构建 UI ──

    def _build_widgets(self):
        s = self.sm
        p = self.p

        main = tk.Frame(self.root, bg=p.bg_primary)
        main.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self._bind_drag(main)

        # ── 顶部栏 ──
        top_bar = tk.Frame(main, bg=p.bg_primary, height=30)
        top_bar.pack(fill=tk.X, padx=6, pady=(6, 0))
        top_bar.pack_propagate(False)
        self._bind_drag(top_bar)

        close_btn = self._make_icon_btn(top_bar, "✕", command=self.hide)
        close_btn.pack(side=tk.RIGHT, padx=(2, 4))

        settings_btn = self._make_icon_btn(top_bar, "⚙", command=self._open_settings)
        settings_btn.pack(side=tk.RIGHT, padx=(0, 2))

        handle = tk.Label(top_bar, text="⠿", bg=p.bg_primary, fg=p.text_tertiary,
                          font=("Segoe UI", 13), cursor="fleur")
        handle.place(relx=0.5, rely=0.5, anchor="center")
        self._bind_drag(handle)

        # ── 搜索栏 ──
        search_frame = tk.Frame(main, bg=p.bg_tertiary, height=48)
        search_frame.pack(fill=tk.X, padx=10, pady=(4, 4))
        search_frame.pack_propagate(False)
        self._bind_drag(search_frame)

        icon_label = tk.Label(search_frame, text="🔍", bg=p.bg_tertiary,
                              fg=p.text_primary, font=("Segoe UI Emoji", 12))
        icon_label.pack(side=tk.LEFT, padx=(8, 4))
        self._bind_drag(icon_label)

        self.entry = tk.Entry(
            search_frame, font=s.get_font('search_input'),
            bg=p.bg_tertiary, fg=p.text_primary,
            insertbackground=p.accent_primary,
            relief=tk.FLAT, highlightthickness=0,
        )
        self.entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4), pady=10)

        self._clear_btn = tk.Label(
            search_frame, text="✕", bg=p.bg_tertiary, fg=p.text_tertiary,
            font=("Segoe UI", 9), cursor="hand2", padx=6)
        self._clear_btn.bind("<Button-1>", lambda e: self._clear_input())
        self._clear_btn.bind("<Enter>", lambda e: self._clear_btn.config(fg=p.text_primary))
        self._clear_btn.bind("<Leave>", lambda e: self._clear_btn.config(fg=p.text_tertiary))

        self.entry.bind("<Key>", self._on_key)
        self.entry.bind("<Down>", self._on_arrow_down)
        self.entry.bind("<Up>", self._on_arrow_up)
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<Tab>", self._on_tab)

        # ── 候选列表 ──
        self._list_frame = tk.Frame(main, bg=p.bg_secondary)
        self._list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 4))

        self.listbox = tk.Listbox(
            self._list_frame, font=("Consolas", 10),
            bg=p.bg_secondary, fg=p.text_primary,
            selectbackground=p.bg_elevated,
            selectforeground=p.accent_primary,
            relief=tk.FLAT, highlightthickness=0,
            activestyle="none",
        )
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<MouseWheel>",
                          lambda e: self.listbox.yview_scroll(-e.delta // 120, "units"))
        self.listbox.bind("<<ListboxSelect>>", self._on_list_select)
        self.listbox.bind("<Double-Button-1>", self._on_double_click)

        # ── 释义面板（初始隐藏）──
        self._def_frame = tk.Frame(main, bg=p.bg_primary)
        self._def_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 10))
        self._bind_drag(self._def_frame)

        # 返回按钮（详情模式下显示）
        self._back_btn = tk.Label(
            self._def_frame, text="← 返回列表",
            font=("Segoe UI", 9), bg=p.bg_primary, fg=p.text_tertiary,
            cursor="hand2", anchor="w",
        )
        self._back_btn.pack(fill=tk.X, pady=(0, 2))
        self._back_btn.bind("<Button-1>", lambda e: self._show_list_mode())
        self._back_btn.bind("<Enter>", lambda e: self._back_btn.config(fg=p.accent_primary))
        self._back_btn.bind("<Leave>", lambda e: self._back_btn.config(fg=p.text_tertiary))

        self.def_title = tk.Label(
            self._def_frame, text="输入单词开始查询…",
            font=s.get_font('result_title', 'bold'),
            bg=p.bg_primary, fg=p.accent_primary, anchor="w",
        )
        # Title row with favorite button
        self._title_row = tk.Frame(self._def_frame, bg=p.bg_primary)
        self._title_row.pack(fill=tk.X, pady=(0, 2))
        self._bind_drag(self._title_row)

        self.def_title = tk.Label(
            self._title_row, text="输入单词开始查询…",
            font=s.get_font('result_title', 'bold'),
            bg=p.bg_primary, fg=p.accent_primary, anchor="w",
        )
        self.def_title.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._bind_drag(self.def_title)

        self._fav_btn = tk.Label(
            self._title_row, text="☆", font=("Segoe UI Emoji", 14),
            bg=p.bg_primary, fg=p.text_tertiary, cursor="hand2", padx=4,
        )
        self._fav_btn.pack(side=tk.RIGHT)
        self._fav_btn.bind("<Button-1>", self._on_toggle_favorite)
        self._fav_btn.bind("<Enter>", lambda e: self._fav_btn.config(fg=p.accent_primary))
        self._fav_btn.bind("<Leave>", lambda e: self._fav_btn.config(
            fg=p.accent_primary if (self.vocabulary and self.vocabulary.is_favorited(
                self.def_title.cget("text"))) else p.text_tertiary))
        self._current_detail_word = ""

        # 星标按钮
        self._star_btn = tk.Label(
            self._title_row, text="◇", font=("Segoe UI Emoji", 14),
            bg=p.bg_primary, fg=p.text_tertiary, cursor="hand2", padx=4,
        )
        self._star_btn.pack(side=tk.RIGHT)
        self._star_btn.bind("<Button-1>", self._on_toggle_star)
        self._star_btn.bind("<Enter>", lambda e: self._star_btn.config(fg="#FFD700"))
        self._star_btn.bind("<Leave>", lambda e: self._star_btn.config(
            fg="#FFD700" if (self.vocabulary and self.vocabulary.is_starred(
                self._current_detail_word)) else p.text_tertiary))

        self.def_text = tk.Text(
            self._def_frame, font=s.get_font('result_body'),
            bg=p.bg_primary, fg=p.text_primary,
            relief=tk.FLAT, highlightthickness=0,
            wrap=tk.WORD, state=tk.DISABLED, cursor="arrow",
        )
        self.def_text.pack(fill=tk.BOTH, expand=True)
        self.def_text.bind("<Button-1>", self._on_copy_definition)

        # 新用户引导 toast 序列
        self._show_guide()

        # 窗口大小拖拽调整手柄
        self._create_resize_handles(main)

    # ── 清空输入 ──

    def _clear_input(self):
        self.entry.delete(0, tk.END)
        self._clear_matches()
        self.entry.focus_set()
        self._clear_btn.pack_forget()
        self._show_list_mode()

    # ── 模式切换：列表模式 / 详情模式 ──

    def _show_list_mode(self):
        """显示候选列表，隐藏释义面板"""
        if self._detail_mode:
            self._def_frame.pack_forget()
            self._list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 4))
            self._detail_mode = False

    def _show_detail_mode(self):
        """显示释义面板，隐藏候选列表"""
        if not self._detail_mode:
            self._list_frame.pack_forget()
            self._def_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 10))
            self._detail_mode = True

    def _on_escape(self, event=None):
        """Escape: 详情模式→列表模式，列表模式→关闭窗口"""
        if self._detail_mode:
            self._show_list_mode()
            self.entry.focus_set()
        else:
            self.hide()

    # ── 搜索逻辑 ──

    def _on_key(self, event):
        if event.keysym in ("Down", "Up", "Return", "Tab", "Escape",
                             "Shift_L", "Shift_R", "Control_L", "Control_R",
                             "Alt_L", "Alt_R"):
            return
        # 详情模式下按键 → 回到列表模式
        if self._detail_mode:
            self._show_list_mode()
        self.root.after(1, self._do_search)

    def _do_search(self):
        query = self.entry.get().strip()
        if query:
            self._clear_btn.pack(side=tk.RIGHT, padx=(0, 6))
        else:
            self._clear_btn.pack_forget()

        if not query:
            self._clear_matches()
            self._show_list_mode()
            return

        # 回到列表模式（如果之前在详情模式）
        self._show_list_mode()

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
            return

        # 限制显示数量避免渲染卡顿
        display = self._matches[:30]

        for m in display:
            word = m["word"]
            pos = m.get("pos", "") or _extract_pos(m.get("definition", ""))
            phon = m.get("phonetic", "")
            defn = m.get("definition", "").split("\n")[0]
            if len(defn) > 22:
                defn = defn[:22] + "…"
            # 星标词汇显示 ◆ 标记
            star_mark = ""
            if self.vocabulary and self.vocabulary.is_starred(word):
                star_mark = "◆ "
            pos_display = f"  {pos}" if pos else ""
            if phon:
                self.listbox.insert(tk.END, f"  {star_mark}{word}{pos_display}  {phon}  {defn}")
            else:
                self.listbox.insert(tk.END, f"  {star_mark}{word}{pos_display}  {defn}")

        # 自动选中第一项（但不显示详情，保持列表模式）
        self.listbox.selection_set(0)
        self.listbox.activate(0)
        self._selected_idx = 0

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
                    time = h.get("time", "")
                    if len(defn) > 18:
                        defn = defn[:18] + "…"
                    self.listbox.insert(tk.END, f"  🕐 {word}  {defn}  {time}")
                self._set_definition("最近查词", "输入新的单词开始查询，或从历史中选择")
                return
        self._set_definition("输入单词开始查询…", "")

    # ── 键盘导航 ──

    def _on_arrow_down(self, event):
        if self._matches:
            self._selected_idx = min(self._selected_idx + 1, len(self._matches) - 1)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self._selected_idx)
            self.listbox.see(self._selected_idx)
        return "break"

    def _on_arrow_up(self, event):
        if self._matches:
            self._selected_idx = max(self._selected_idx - 1, 0)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self._selected_idx)
            self.listbox.see(self._selected_idx)
        return "break"

    def _on_enter(self, event):
        # 有 AI 待翻译 → 触发 AI
        if self._ai_pending_query:
            self._trigger_ai(self._ai_pending_query)
            return "break"
        # 有选中词条 → 显示详情
        if 0 <= self._selected_idx < len(self._matches):
            self._show_definition(self._selected_idx)
        return "break"

    def _on_tab(self, event):
        query = self.entry.get().strip()
        if query:
            self._trigger_ai(query)
        return "break"

    def _trigger_ai(self, query: str):
        self._set_definition("🤖 AI 翻译中…", f'正在翻译 "{query}"，请稍候…')
        self._show_detail_mode()
        self._current_detail_word = query
        self._update_fav_button()
        self._update_star_button()
        self.on_translate(query, self._on_ai_result, self._on_ai_error)

    def _on_ai_result(self, text: str):
        self.root.after(0, lambda: self._set_definition("🤖 AI 翻译结果", text))

    def _on_ai_error(self, error: str):
        self.root.after(0, lambda: self._set_definition("翻译失败", f"错误: {error}"))

    # ── 列表交互 ──

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
                self._show_definition(idx)

    # ── 释义显示 ──
    def _show_definition(self, idx: int, record_history=True):
        """选中即展示完整释义（切换到详情模式）"""
        if 0 <= idx < len(self._matches):
            m = self._matches[idx]
            word = m["word"]
            defn = m.get("text") or m.get("definition", "无释义")
            self._set_definition(word, defn)
            self._show_detail_mode()  # 切换到详情面板
            self._current_detail_word = word
            self._update_fav_button()
            self._update_star_button()
            if record_history and self.history:
                self.history.add(word, m.get("definition", "")[:80])

    def _update_fav_button(self):
        """Update the favorite button appearance based on current word."""
        if not self.vocabulary:
            return
        word = self._current_detail_word
        if word and self.vocabulary.is_favorited(word):
            self._fav_btn.config(text="★", fg=self.p.accent_primary)
        else:
            self._fav_btn.config(text="☆", fg=self.p.text_tertiary)

    def _on_toggle_favorite(self, event=None):
        """Toggle favorite status for the current word."""
        if not self.vocabulary or not self._current_detail_word:
            return
        word = self._current_detail_word
        content = self.def_text.get("1.0", tk.END).strip()
        now_fav = self.vocabulary.toggle(word, content)
        self._update_fav_button()
        self._update_star_button()
        if now_fav:
            self._show_toast(f"已收藏 \"{word}\" ★", 1500)
        else:
            self._show_toast(f"已取消收藏 \"{word}\"", 1500)

    def _on_toggle_star(self, event=None):
        """Toggle star status for the current word."""
        if not self.vocabulary or not self._current_detail_word:
            return
        word = self._current_detail_word
        if not self.vocabulary.is_favorited(word):
            # 先收藏，再加星标
            content = self.def_text.get("1.0", tk.END).strip()
            self.vocabulary.add(word, content)
        now_starred = self.vocabulary.toggle_star(word)
        self._update_fav_button()
        self._update_star_button()
        if now_starred:
            self._show_toast(f"已星标 \"{word}\" ◆", 1500)
        else:
            self._show_toast(f"已取消星标 \"{word}\"", 1500)

    def _update_star_button(self):
        """Update the star button appearance based on current word."""
        if not self.vocabulary:
            return
        word = self._current_detail_word
        if word and self.vocabulary.is_starred(word):
            self._star_btn.config(text="◆", fg="#FFD700")
        else:
            self._star_btn.config(text="◇", fg=self.p.text_tertiary)

    def _set_definition(self, title: str, content: str):
        self.def_title.config(text=title)
        self.def_text.config(state=tk.NORMAL)
        self.def_text.delete("1.0", tk.END)
        if content:
            self.def_text.insert("1.0", content)
        self.def_text.config(state=tk.DISABLED)

    # ── 复制释义 ──

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

    # ── 窗口显隐 ──

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.entry.focus_set()
        self.entry.select_range(0, tk.END)
        self._visible = True
        # 淡入动画
        self.anim.fade_in(self.root, duration=150,
                          from_alpha=0.3, to_alpha=self.opacity)
        if not self.entry.get().strip():
            self._clear_matches()

    def _save_position(self):
        if "window_position" not in self.cfg:
            self.cfg["window_position"] = {}
        self.cfg["window_position"]["x"] = self.root.winfo_x()
        self.cfg["window_position"]["y"] = self.root.winfo_y()
        # Also save current window size
        self.cfg["ui"]["width"] = self.root.winfo_width()
        self.cfg["ui"]["height"] = self.root.winfo_height()

    def hide(self):
        self._save_position()
        # 淡出动画
        def do_hide():
            self.root.withdraw()
            self.root.attributes("-alpha", self.opacity)
            self._visible = False
        self.anim.fade_out(self.root, duration=100,
                           from_alpha=self.opacity, to_alpha=0.0,
                           on_complete=do_hide)
        if self._settings_panel:
            self._settings_panel._close()
            self._settings_panel = None

    def toggle(self):
        if self._visible:
            self.hide()
        else:
            self.show()

    def run(self):
        self.root.withdraw()
        # Start system theme polling if using "system" theme
        if self._config_theme == 'system':
            self.root.after(10000, self._poll_system_theme)
        self.root.mainloop()
