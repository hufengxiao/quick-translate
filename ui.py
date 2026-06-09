"""主窗口 UI - Apple Spotlight 风格（使用设计系统）"""
import tkinter as tk
from tkinter import font as tkfont
import ctypes
import traceback
from typing import Optional, Callable, List, Dict

from styles import StyleManager
from animations import AnimationEngine


class SpotlightUI:
    """Spotlight 风格的查词窗口"""

    def __init__(self, config: dict,
                 on_search: Callable[[str], List[Dict[str, str]]],
                 on_translate: Callable[[str, Callable, Optional[Callable]], None],
                 history=None):
        self.cfg = config
        self.on_search = on_search
        self.on_translate = on_translate
        self.history = history

        # 设计系统
        self.sm = StyleManager('dark')
        self.p = self.sm.palette

        self.opacity = config["ui"]["opacity"]
        self._visible = False
        self._selected_idx = -1
        self._matches: List[Dict[str, str]] = []
        self._settings_win = None
        self._toast_after = None
        self._ai_pending_query = None
        self._detail_mode = False  # False=list mode, True=detail mode

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

        self.root.bind("<Escape>", lambda e: self.hide())
        self.root.bind("<FocusIn>", self._on_focus_in)
        self.root.bind("<FocusOut>", self._on_focus_out)
        self._drag_x = 0
        self._drag_y = 0

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
        dx = self.root.winfo_pointerx() - self._drag_x
        dy = self.root.winfo_pointery() - self._drag_y
        self.root.geometry(f"+{self._win_x + dx}+{self._win_y + dy}")

    # ── 失焦/获焦 ──

    def _on_focus_in(self, event):
        self.root.attributes("-alpha", self.opacity)

    def _on_focus_out(self, event):
        if self._settings_win is None:
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
        if self._settings_win is not None:
            self._settings_win.destroy()
            self._settings_win = None
            return

        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", self.opacity)
        win.configure(bg=self.p.bg_tertiary)
        self._settings_win = win

        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        win.geometry(f"220x70+{rx + rw - 220}+{ry + 5}")

        try:
            hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
            pref = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, ctypes.byref(pref), ctypes.sizeof(pref))
        except Exception:
            pass

        tk.Label(win, text="透明度", font=("Segoe UI", 9),
                 bg=self.p.bg_tertiary, fg=self.p.text_primary).pack(pady=(8, 0))

        var = tk.DoubleVar(value=self.opacity)

        def on_slider(v):
            self._set_opacity(float(v))
            win.attributes("-alpha", float(v))

        tk.Scale(
            win, from_=0.1, to=0.9, resolution=0.1,
            orient=tk.HORIZONTAL, variable=var, command=on_slider,
            bg=self.p.bg_tertiary, fg=self.p.text_primary,
            highlightthickness=0, troughcolor=self.p.bg_primary,
            sliderrelief=tk.FLAT, length=190, showvalue=True,
            bd=0, font=("Segoe UI", 8),
        ).pack(padx=10, pady=(0, 6))

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

        self.def_title = tk.Label(
            self._def_frame, text="输入单词开始查询…",
            font=s.get_font('result_title', 'bold'),
            bg=p.bg_primary, fg=p.accent_primary, anchor="w",
        )
        self.def_title.pack(fill=tk.X, pady=(0, 2))
        self._bind_drag(self.def_title)

        self.def_text = tk.Text(
            self._def_frame, font=s.get_font('result_body'),
            bg=p.bg_primary, fg=p.text_primary,
            relief=tk.FLAT, highlightthickness=0,
            wrap=tk.WORD, state=tk.DISABLED, cursor="arrow",
        )
        self.def_text.pack(fill=tk.BOTH, expand=True)
        self.def_text.bind("<Button-1>", self._on_copy_definition)

        # 首次启动 toast
        self.root.after(500, lambda: self._show_toast(
            "Shift+Ctrl+M 唤出  |  ↑↓选择  |  Enter AI翻译", 4000))

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
            self.listbox.insert(tk.END, f"  🤖 本地无结果，按 Enter AI 翻译")
            self._ai_pending_query = query
            return

        for m in self._matches:
            word = m["word"]
            defn = m.get("definition", "").split("\n")[0]
            if len(defn) > 22:
                defn = defn[:22] + "…"
            self.listbox.insert(tk.END, f"  {word}  {defn}")

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
                word = self._matches[idx]["word"]
                self._trigger_ai(word)

    # ── 释义显示 ──
    def _show_definition(self, idx: int, record_history=True):
        """选中即展示完整释义（切换到详情模式）"""
        if 0 <= idx < len(self._matches):
            m = self._matches[idx]
            word = m["word"]
            defn = m.get("text") or m.get("definition", "无释义")
            self._set_definition(word, defn)
            self._show_detail_mode()  # 切换到详情面板
            if record_history and self.history:
                self.history.add(word, m.get("definition", "")[:80])

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
