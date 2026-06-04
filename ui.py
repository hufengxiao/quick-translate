"""主窗口 UI - 模拟 macOS Spotlight 风格"""
import tkinter as tk
from tkinter import font as tkfont
import ctypes
import traceback
from typing import Optional, Callable, List, Dict


class SpotlightUI:
    """Spotlight 风格的查词窗口"""

    def __init__(self, config: dict,
                 on_search: Callable[[str], List[Dict[str, str]]],
                 on_translate: Callable[[str, Callable, Optional[Callable]], None]):
        self.cfg = config["ui"]
        self.on_search = on_search
        self.on_translate = on_translate
        self.opacity = self.cfg["opacity"]
        self._visible = False
        self._selected_idx = -1
        self._matches: List[Dict[str, str]] = []
        self._settings_win = None

        self._build_window()
        self._build_widgets()

    def _build_window(self):
        self.root = tk.Tk()
        self.root.title("Quick Translate")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self.opacity)
        self.root.configure(bg=self.cfg["bg_color"])

        w, h = self.cfg["width"], self.cfg["height"]
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 3
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        # Windows 11 圆角
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            preference = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(preference), ctypes.sizeof(preference)
            )
        except Exception:
            pass

        self.root.bind("<Escape>", lambda e: self.hide())
        self.root.bind("<FocusIn>", self._on_focus_in)
        self.root.bind("<FocusOut>", self._on_focus_out)

        # 拖拽状态
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

    # ── 按钮交互状态 ──

    def _make_icon_btn(self, parent, text, normal_fg="#585b70",
                       hover_fg="#cdd6f4", press_fg="#89b4fa",
                       hover_bg="#313244", press_bg="#45475a",
                       command=None):
        """创建带 hover / press 状态的图标按钮"""
        bg = self.cfg["bg_color"]
        btn = tk.Label(parent, text=text, bg=bg, fg=normal_fg,
                       font=("Segoe UI", 11), cursor="hand2", padx=4, pady=2)

        def on_enter(e):
            btn.config(fg=hover_fg, bg=hover_bg)

        def on_leave(e):
            btn.config(fg=normal_fg, bg=bg)

        def on_press(e):
            btn.config(fg=press_fg, bg=press_bg)

        def on_release(e):
            btn.config(fg=hover_fg, bg=hover_bg)
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

        cfg = self.cfg
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", self.opacity)  # 跟随主窗口透明度
        win.configure(bg=cfg["entry_bg"])
        self._settings_win = win

        # 定位在主窗口右侧下方
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        win.geometry(f"220x70+{rx + rw - 220}+{ry + 5}")

        # 圆角
        try:
            hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
            pref = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, ctypes.byref(pref), ctypes.sizeof(pref))
        except Exception:
            pass

        tk.Label(win, text="透明度", font=("Segoe UI", 9),
                 bg=cfg["entry_bg"], fg="#cdd6f4").pack(pady=(8, 0))

        var = tk.DoubleVar(value=self.opacity)

        def on_slider(v):
            self._set_opacity(float(v))
            win.attributes("-alpha", float(v))  # 弹窗也跟着变

        slider = tk.Scale(
            win, from_=0.1, to=0.9, resolution=0.1,
            orient=tk.HORIZONTAL, variable=var,
            command=on_slider,
            bg=cfg["entry_bg"], fg="#cdd6f4",
            highlightthickness=0, troughcolor=cfg["bg_color"],
            sliderrelief=tk.FLAT, length=190, showvalue=True,
            bd=0, font=("Segoe UI", 8),
        )
        slider.pack(padx=10, pady=(0, 6))

        def close_settings(e=None):
            if self._settings_win:
                self._settings_win.destroy()
                self._settings_win = None

        win.bind("<FocusOut>", close_settings)
        win.focus_set()

    def _set_opacity(self, value):
        self.opacity = value
        self.root.attributes("-alpha", self.opacity)

    # ── 构建 UI ──

    def _build_widgets(self):
        cfg = self.cfg
        fs = cfg["font_size"]
        default_font = tkfont.Font(family="Segoe UI", size=fs)
        small_font = tkfont.Font(family="Segoe UI", size=fs - 2)
        bold_font = tkfont.Font(family="Segoe UI", size=fs, weight="bold")
        mono_font = tkfont.Font(family="Consolas", size=10)

        main = tk.Frame(self.root, bg=cfg["bg_color"])
        main.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self._bind_drag(main)

        # ── 顶部栏 ──
        top_bar = tk.Frame(main, bg=cfg["bg_color"], height=30)
        top_bar.pack(fill=tk.X, padx=6, pady=(6, 0))
        top_bar.pack_propagate(False)
        self._bind_drag(top_bar)

        # 右侧按钮（先 pack，靠右）
        close_btn = self._make_icon_btn(top_bar, "✕", command=self.hide)
        close_btn.pack(side=tk.RIGHT, padx=(2, 4))

        settings_btn = self._make_icon_btn(top_bar, "⚙", command=self._open_settings)
        settings_btn.pack(side=tk.RIGHT, padx=(0, 2))

        # 拖拽把手 — 相对 top_bar 居中（top_bar 是全宽的）
        handle = tk.Label(top_bar, text="⠿", bg=cfg["bg_color"], fg="#585b70",
                          font=("Segoe UI", 13), cursor="fleur")
        handle.place(relx=0.5, rely=0.5, anchor="center")
        self._bind_drag(handle)

        # ── 搜索栏 ──
        search_frame = tk.Frame(main, bg=cfg["entry_bg"], height=40)
        search_frame.pack(fill=tk.X, padx=10, pady=(4, 4))
        search_frame.pack_propagate(False)
        self._bind_drag(search_frame)

        icon_label = tk.Label(search_frame, text="🔍", bg=cfg["entry_bg"],
                              fg=cfg["fg_color"], font=("Segoe UI Emoji", 12))
        icon_label.pack(side=tk.LEFT, padx=(8, 4))
        self._bind_drag(icon_label)

        self.entry = tk.Entry(
            search_frame, font=default_font,
            bg=cfg["entry_bg"], fg=cfg["fg_color"],
            insertbackground=cfg["accent_color"],
            relief=tk.FLAT, highlightthickness=0,
        )
        self.entry.pack(fill=tk.BOTH, expand=True, padx=(0, 8), pady=8)

        self.entry.bind("<Key>", self._on_key)
        self.entry.bind("<Down>", self._on_arrow_down)
        self.entry.bind("<Up>", self._on_arrow_up)
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<Tab>", self._on_tab)

        # ── 候选列表 ──
        list_frame = tk.Frame(main, bg=cfg["list_bg"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 4))

        self.listbox = tk.Listbox(
            list_frame, font=mono_font,
            bg=cfg["list_bg"], fg=cfg["fg_color"],
            selectbackground=cfg["highlight_bg"],
            selectforeground=cfg["accent_color"],
            relief=tk.FLAT, highlightthickness=0,
            activestyle="none",
        )
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<MouseWheel>",
                          lambda e: self.listbox.yview_scroll(-e.delta // 120, "units"))
        self.listbox.bind("<<ListboxSelect>>", self._on_list_select)
        self.listbox.bind("<Double-Button-1>", self._on_double_click)

        # ── 释义面板 ──
        def_frame = tk.Frame(main, bg=cfg["bg_color"])
        def_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 2))
        self._bind_drag(def_frame)

        self.def_title = tk.Label(
            def_frame, text="输入单词开始查询…", font=bold_font,
            bg=cfg["bg_color"], fg=cfg["accent_color"], anchor="w",
        )
        self.def_title.pack(fill=tk.X, pady=(0, 2))
        self._bind_drag(self.def_title)

        self.def_text = tk.Text(
            def_frame, font=small_font,
            bg=cfg["bg_color"], fg=cfg["fg_color"],
            relief=tk.FLAT, highlightthickness=0,
            wrap=tk.WORD, state=tk.DISABLED, cursor="arrow",
        )
        self.def_text.pack(fill=tk.BOTH, expand=True)

        # ── 底栏 ──
        bottom = tk.Frame(main, bg=cfg["bg_color"], height=20)
        bottom.pack(fill=tk.X, padx=10, pady=(0, 6))
        bottom.pack_propagate(False)
        self._bind_drag(bottom)

        tk.Label(bottom, text="Esc关闭  ↑↓选择  Enter展开  Tab翻译",
                 font=("Segoe UI", 8), bg=cfg["bg_color"], fg="#45475a"
                 ).pack(side=tk.LEFT)

    # ── 搜索逻辑 ──

    def _on_key(self, event):
        if event.keysym in ("Down", "Up", "Return", "Tab", "Escape",
                             "Shift_L", "Shift_R", "Control_L", "Control_R",
                             "Alt_L", "Alt_R"):
            return
        self.root.after(1, self._do_search)

    def _do_search(self):
        query = self.entry.get().strip()
        if not query:
            self._clear_matches()
            return
        try:
            self._matches = self.on_search(query)
            self._update_listbox()
        except Exception as e:
            self._set_definition("搜索出错", str(e))
            traceback.print_exc()

    def _update_listbox(self):
        self.listbox.delete(0, tk.END)
        self._selected_idx = -1
        for m in self._matches:
            word = m["word"]
            defn = m.get("definition", "").split("\n")[0]
            max_len = 20
            if len(defn) > max_len:
                defn = defn[:max_len] + "…"
            self.listbox.insert(tk.END, f"  {word}  {defn}")
        if self._matches:
            self.listbox.selection_set(0)
            self.listbox.activate(0)
            self._selected_idx = 0
            self._show_definition(0)

    def _clear_matches(self):
        self._matches = []
        self.listbox.delete(0, tk.END)
        self._set_definition("输入单词开始查询…", "")

    # ── 键盘导航 ──

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
        if 0 <= self._selected_idx < len(self._matches):
            self._show_full_definition(self._selected_idx)
        return "break"

    def _on_tab(self, event):
        query = self.entry.get().strip()
        if query:
            self._set_definition("🤖 AI 翻译中…", "正在调用 AI 翻译引擎，请稍候…")
            self.on_translate(query, self._on_ai_result, self._on_ai_error)
        return "break"

    def _on_ai_result(self, text: str):
        self.root.after(0, lambda: self._set_definition("🤖 AI 翻译结果", text))

    def _on_ai_error(self, error: str):
        self.root.after(0, lambda: self._set_definition("翻译失败", f"错误: {error}"))

    # ── 列表交互 ──

    def _on_list_select(self, event):
        sel = self.listbox.curselection()
        if sel:
            self._selected_idx = sel[0]
            self._show_definition(self._selected_idx)

    def _on_double_click(self, event):
        sel = self.listbox.curselection()
        if sel:
            self._selected_idx = sel[0]
            self._show_full_definition(self._selected_idx)

    # ── 释义显示 ──

    def _show_definition(self, idx: int):
        if 0 <= idx < len(self._matches):
            m = self._matches[idx]
            self._set_definition(m["word"], m.get("definition", "无释义"))

    def _show_full_definition(self, idx: int):
        if 0 <= idx < len(self._matches):
            m = self._matches[idx]
            full = m.get("definition", "无释义")
            self._set_definition(f"📖 {m['word']}", full)

    def _set_definition(self, title: str, content: str):
        self.def_title.config(text=title)
        self.def_text.config(state=tk.NORMAL)
        self.def_text.delete("1.0", tk.END)
        if content:
            self.def_text.insert("1.0", content)
        self.def_text.config(state=tk.DISABLED)

    # ── 窗口显隐 ──

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.entry.focus_set()
        self.entry.select_range(0, tk.END)
        self._visible = True

    def hide(self):
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
