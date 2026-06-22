"""
可视化设置面板 — 不再需要手动编辑 JSON
分组展示所有配置项，保存后立即生效
"""
import tkinter as tk
import ctypes
from src.utils.autostart import set_autostart, is_autostart_enabled
from src.utils.context_menu import is_installed as is_context_menu_installed, set_enabled as set_context_menu_enabled


class SettingsPanel:
    """全功能设置面板"""

    SECTION_BG = None  # set from palette

    def __init__(self, parent, config: dict, palette, style_manager,
                 on_save=None, on_theme_change=None):
        """
        Args:
            parent: 父窗口 (root)
            config: 配置字典 (来自 config.py)
            palette: 当前 ColorPalette
            style_manager: StyleManager 实例
            on_save: 保存回调 fn(new_cfg)
            on_theme_change: 主题切换回调 fn(theme_name)
        """
        self.parent = parent
        self.cfg = config
        self.p = palette
        self.sm = style_manager
        self.on_save = on_save
        self.on_theme_change = on_theme_change
        self.win = None
        self._vars = {}

    # ── public ──

    def show(self):
        """弹出设置面板（如果已打开则关闭）"""
        if self.win is not None:
            self.win.destroy()
            self.win = None
            return

        win = tk.Toplevel(self.parent)
        self.win = win
        win.title("设置")
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.96)
        win.configure(bg=self.p.bg_tertiary)

        # 位置：紧跟主窗口右侧
        rx = self.parent.winfo_x()
        ry = self.parent.winfo_y()
        rw = self.parent.winfo_width()
        panel_w = 320
        panel_h = 520
        # 如果右侧空间不够，放到左侧
        sw = win.winfo_screenwidth()
        if rx + rw + panel_w + 10 > sw:
            px = rx - panel_w - 6
        else:
            px = rx + rw + 6
        py = ry
        win.geometry(f"{panel_w}x{panel_h}+{px}+{py}")

        # 圆角
        try:
            hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
            pref = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, ctypes.byref(pref), ctypes.sizeof(pref))
        except Exception:
            pass

        # ── 标题栏 ──
        title_bar = tk.Frame(win, bg=self.p.bg_primary, height=36)
        title_bar.pack(fill=tk.X)
        title_bar.pack_propagate(False)

        tk.Label(title_bar, text="  ⚙ 设置", font=("Segoe UI", 12, "bold"),
                 bg=self.p.bg_primary, fg=self.p.text_primary,
                 anchor="w").pack(side=tk.LEFT, padx=8, fill=tk.X, expand=True)

        close_btn = tk.Label(title_bar, text="✕", font=("Segoe UI", 11),
                             bg=self.p.bg_primary, fg=self.p.text_tertiary,
                             cursor="hand2", padx=8)
        close_btn.pack(side=tk.RIGHT)
        close_btn.bind("<Button-1>", lambda e: self._close())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg=self.p.text_primary))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg=self.p.text_tertiary))

        # ── 可滚动内容区 ──
        container = tk.Frame(win, bg=self.p.bg_tertiary)
        container.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(container, bg=self.p.bg_tertiary,
                           highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(container, orient=tk.VERTICAL,
                                 command=canvas.yview)
        self._content = tk.Frame(canvas, bg=self.p.bg_tertiary)

        self._content.bind("<Configure>",
                           lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel, add="+")

        # ── 构建各分组 ──
        self._build_appearance_section()
        self._build_hotkey_section()
        self._build_ai_section()
        self._build_clipboard_section()
        self._build_autostart_section()
        self._build_context_menu_section()

        # ── 底部按钮 ──
        btn_frame = tk.Frame(win, bg=self.p.bg_primary, height=44)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        btn_frame.pack_propagate(False)

        cancel_btn = self._make_button(btn_frame, "取消", self._close)
        cancel_btn.pack(side=tk.RIGHT, padx=(0, 12), pady=8)

        save_btn = self._make_button(btn_frame, "保存", self._save, accent=True)
        save_btn.pack(side=tk.RIGHT, padx=(0, 6), pady=8)

        reset_btn = self._make_button(btn_frame, "恢复默认", self._reset_defaults)
        reset_btn.pack(side=tk.LEFT, padx=12, pady=8)

        # 关闭行为
        win.bind("<Escape>", lambda e: self._close())
        win.protocol("WM_DELETE_WINDOW", self._close)
        win.focus_set()

    # ── 分组构建 ──

    def _build_appearance_section(self):
        self._section_header("外观")

        # 主题
        self._label("主题")
        theme_var = tk.StringVar(value=self.cfg.get("ui", {}).get("theme", "dark"))
        self._vars["ui.theme"] = theme_var
        theme_frame = tk.Frame(self._content, bg=self.p.bg_tertiary)
        theme_frame.pack(fill=tk.X, padx=16, pady=(0, 8))
        for text, val in [("跟随系统", "system"), ("深色", "dark"), ("浅色", "light"), ("高对比", "high_contrast")]:
            rb = tk.Radiobutton(
                theme_frame, text=text, variable=theme_var, value=val,
                font=("Segoe UI", 10), bg=self.p.bg_tertiary,
                fg=self.p.text_primary, selectcolor=self.p.bg_elevated,
                activebackground=self.p.bg_tertiary,
                activeforeground=self.p.accent_primary,
                command=lambda: self._preview_theme(theme_var.get()),
            )
            rb.pack(side=tk.LEFT, padx=(0, 12))

        # 透明度
        self._label("透明度")
        opacity_var = tk.DoubleVar(value=self.cfg.get("ui", {}).get("opacity", 0.95))
        self._vars["ui.opacity"] = opacity_var
        opacity_frame = tk.Frame(self._content, bg=self.p.bg_tertiary)
        opacity_frame.pack(fill=tk.X, padx=16, pady=(0, 8))
        tk.Scale(
            opacity_frame, from_=0.3, to=1.0, resolution=0.05,
            orient=tk.HORIZONTAL, variable=opacity_var,
            bg=self.p.bg_tertiary, fg=self.p.text_primary,
            highlightthickness=0, troughcolor=self.p.bg_primary,
            sliderrelief=tk.FLAT, length=220, showvalue=True,
            bd=0, font=("Segoe UI", 9),
        ).pack(fill=tk.X)

        # 字体大小
        self._label("字体大小")
        font_var = tk.IntVar(value=self.cfg.get("ui", {}).get("font_size", 13))
        self._vars["ui.font_size"] = font_var
        font_frame = tk.Frame(self._content, bg=self.p.bg_tertiary)
        font_frame.pack(fill=tk.X, padx=16, pady=(0, 8))
        tk.Scale(
            font_frame, from_=8, to=24, resolution=1,
            orient=tk.HORIZONTAL, variable=font_var,
            bg=self.p.bg_tertiary, fg=self.p.text_primary,
            highlightthickness=0, troughcolor=self.p.bg_primary,
            sliderrelief=tk.FLAT, length=220, showvalue=True,
            bd=0, font=("Segoe UI", 9),
        ).pack(fill=tk.X)

        # 动画速度
        self._label("动画速度 (倍率)")
        anim_var = tk.DoubleVar(value=self.cfg.get("ui", {}).get("animation_speed", 1.0))
        self._vars["ui.animation_speed"] = anim_var
        anim_frame = tk.Frame(self._content, bg=self.p.bg_tertiary)
        anim_frame.pack(fill=tk.X, padx=16, pady=(0, 8))
        tk.Scale(
            anim_frame, from_=0.25, to=3.0, resolution=0.25,
            orient=tk.HORIZONTAL, variable=anim_var,
            bg=self.p.bg_tertiary, fg=self.p.text_primary,
            highlightthickness=0, troughcolor=self.p.bg_primary,
            sliderrelief=tk.FLAT, length=220, showvalue=True,
            bd=0, font=("Segoe UI", 9),
        ).pack(fill=tk.X)

    def _build_hotkey_section(self):
        self._section_header("快捷键")

        hk = self.cfg.get("hotkey", {})

        row = tk.Frame(self._content, bg=self.p.bg_tertiary)
        row.pack(fill=tk.X, padx=16, pady=(0, 4))

        shift_var = tk.BooleanVar(value=hk.get("shift", True))
        ctrl_var = tk.BooleanVar(value=hk.get("ctrl", True))
        alt_var = tk.BooleanVar(value=hk.get("alt", False))
        self._vars["hotkey.shift"] = shift_var
        self._vars["hotkey.ctrl"] = ctrl_var
        self._vars["hotkey.alt"] = alt_var

        for text, var in [("Shift", shift_var), ("Ctrl", ctrl_var), ("Alt", alt_var)]:
            cb = tk.Checkbutton(
                row, text=text, variable=var,
                font=("Segoe UI", 10), bg=self.p.bg_tertiary,
                fg=self.p.text_primary, selectcolor=self.p.bg_elevated,
                activebackground=self.p.bg_tertiary,
                activeforeground=self.p.accent_primary,
            )
            cb.pack(side=tk.LEFT, padx=(0, 12))

        # 按键
        self._label("触发键")
        key_var = tk.StringVar(value=hk.get("key", "m"))
        self._vars["hotkey.key"] = key_var
        key_entry = tk.Entry(
            self._content, textvariable=key_var, width=6,
            font=("Segoe UI", 12), bg=self.p.bg_primary,
            fg=self.p.text_primary, insertbackground=self.p.accent_primary,
            relief=tk.FLAT, highlightthickness=1,
            highlightcolor=self.p.accent_primary,
            highlightbackground=self.p.border_subtle,
        )
        key_entry.pack(padx=16, pady=(0, 8), anchor="w")

        # 提示
        tk.Label(self._content, text="修改后需重启程序生效",
                 font=("Segoe UI", 9), bg=self.p.bg_tertiary,
                 fg=self.p.text_tertiary).pack(padx=16, pady=(0, 8), anchor="w")

    def _build_ai_section(self):
        self._section_header("AI 翻译")

        ai = self.cfg.get("ai", {})

        # 启用
        enabled_var = tk.BooleanVar(value=ai.get("enabled", True))
        self._vars["ai.enabled"] = enabled_var
        cb = tk.Checkbutton(
            self._content, text="启用 AI 翻译", variable=enabled_var,
            font=("Segoe UI", 10), bg=self.p.bg_tertiary,
            fg=self.p.text_primary, selectcolor=self.p.bg_elevated,
            activebackground=self.p.bg_tertiary,
            activeforeground=self.p.accent_primary,
        )
        cb.pack(padx=16, pady=(0, 8), anchor="w")

        # API 地址
        self._label("API 地址")
        base_var = tk.StringVar(value=ai.get("api_base", ""))
        self._vars["ai.api_base"] = base_var
        self._entry(base_var)

        # API 密钥
        self._label("API 密钥")
        key_var = tk.StringVar(value=ai.get("api_key", ""))
        self._vars["ai.api_key"] = key_var
        self._entry(key_var, show="•")

        # 模型
        self._label("模型")
        model_var = tk.StringVar(value=ai.get("model", ""))
        self._vars["ai.model"] = model_var
        self._entry(model_var)

    def _build_clipboard_section(self):
        self._section_header("剪贴板")

        clip = self.cfg.get("clipboard", {})

        # 启用监听
        mon_var = tk.BooleanVar(value=clip.get("monitor_enabled", False))
        self._vars["clipboard.monitor_enabled"] = mon_var
        cb = tk.Checkbutton(
            self._content, text="监听剪贴板自动翻译", variable=mon_var,
            font=("Segoe UI", 10), bg=self.p.bg_tertiary,
            fg=self.p.text_primary, selectcolor=self.p.bg_elevated,
            activebackground=self.p.bg_tertiary,
            activeforeground=self.p.accent_primary,
        )
        cb.pack(padx=16, pady=(0, 8), anchor="w")

        # 最小长度
        self._label("最小字符数")
        min_var = tk.IntVar(value=clip.get("min_length", 2))
        self._vars["clipboard.min_length"] = min_var
        min_frame = tk.Frame(self._content, bg=self.p.bg_tertiary)
        min_frame.pack(fill=tk.X, padx=16, pady=(0, 12))
        tk.Scale(
            min_frame, from_=1, to=10, resolution=1,
            orient=tk.HORIZONTAL, variable=min_var,
            bg=self.p.bg_tertiary, fg=self.p.text_primary,
            highlightthickness=0, troughcolor=self.p.bg_primary,
            sliderrelief=tk.FLAT, length=220, showvalue=True,
            bd=0, font=("Segoe UI", 9),
        ).pack(fill=tk.X)

    def _build_autostart_section(self):
        self._section_header("启动")

        # 检测实际注册表状态
        current_state = is_autostart_enabled()
        autostart_var = tk.BooleanVar(value=current_state)
        self._vars["autostart.enabled"] = autostart_var

        cb = tk.Checkbutton(
            self._content, text="开机自启动", variable=autostart_var,
            font=("Segoe UI", 10), bg=self.p.bg_tertiary,
            fg=self.p.text_primary, selectcolor=self.p.bg_elevated,
            activebackground=self.p.bg_tertiary,
            activeforeground=self.p.accent_primary,
        )
        cb.pack(padx=16, pady=(0, 4), anchor="w")

        tk.Label(self._content, text="开启后 Windows 启动时自动运行",
                 font=("Segoe UI", 9), bg=self.p.bg_tertiary,
                 fg=self.p.text_tertiary).pack(padx=16, pady=(0, 12), anchor="w")

    def _build_context_menu_section(self):
        self._section_header("右键菜单")

        # 检测实际注册表状态
        current_state = is_context_menu_installed()
        ctx_var = tk.BooleanVar(value=current_state)
        self._vars["context_menu.enabled"] = ctx_var

        cb = tk.Checkbutton(
            self._content, text="添加右键菜单翻译", variable=ctx_var,
            font=("Segoe UI", 10), bg=self.p.bg_tertiary,
            fg=self.p.text_primary, selectcolor=self.p.bg_elevated,
            activebackground=self.p.bg_tertiary,
            activeforeground=self.p.accent_primary,
        )
        cb.pack(padx=16, pady=(0, 4), anchor="w")

        tk.Label(self._content, text="右键文件/文件夹时显示\"用 Quick Translate 翻译\"",
                 font=("Segoe UI", 9), bg=self.p.bg_tertiary,
                 fg=self.p.text_tertiary).pack(padx=16, pady=(0, 12), anchor="w")

    # ── 辅助组件 ──

    def _section_header(self, text):
        frame = tk.Frame(self._content, bg=self.p.bg_tertiary)
        frame.pack(fill=tk.X, padx=16, pady=(12, 4))
        tk.Label(frame, text=text, font=("Segoe UI", 11, "bold"),
                 bg=self.p.bg_tertiary, fg=self.p.accent_primary,
                 anchor="w").pack(side=tk.LEFT)
        # 分隔线
        sep = tk.Frame(frame, bg=self.p.border_subtle, height=1)
        sep.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0), pady=6)

    def _label(self, text):
        tk.Label(self._content, text=text, font=("Segoe UI", 9),
                 bg=self.p.bg_tertiary, fg=self.p.text_secondary,
                 anchor="w").pack(padx=16, pady=(4, 0), fill=tk.X)

    def _entry(self, var, show=None):
        e = tk.Entry(
            self._content, textvariable=var,
            font=("Segoe UI", 10), bg=self.p.bg_primary,
            fg=self.p.text_primary, insertbackground=self.p.accent_primary,
            relief=tk.FLAT, highlightthickness=1,
            highlightcolor=self.p.accent_primary,
            highlightbackground=self.p.border_subtle,
        )
        if show:
            e.config(show=show)
        e.pack(fill=tk.X, padx=16, pady=(0, 8))

    def _make_button(self, parent, text, command, accent=False):
        bg = self.p.accent_primary if accent else self.p.bg_elevated
        fg = "#ffffff" if accent else self.p.text_primary
        btn = tk.Label(parent, text=text, font=("Segoe UI", 10),
                       bg=bg, fg=fg, padx=14, pady=4, cursor="hand2")
        btn.bind("<Button-1>", lambda e: command())
        hover_bg = self.p.accent_secondary if accent else self.p.highlight_bg if hasattr(self.p, 'highlight_bg') else self.p.bg_tertiary

        def on_enter(e):
            btn.config(bg=hover_bg)

        def on_leave(e):
            btn.config(bg=bg)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    # ── 操作 ──

    def _preview_theme(self, theme_name):
        """预览主题切换（不保存）"""
        if self.on_theme_change:
            self.on_theme_change(theme_name)

    def _save(self):
        """保存设置到配置"""
        ui = self.cfg.setdefault("ui", {})
        hk = self.cfg.setdefault("hotkey", {})
        ai = self.cfg.setdefault("ai", {})
        clip = self.cfg.setdefault("clipboard", {})
        ctx = self.cfg.setdefault("context_menu", {})

        # 外观
        ui["theme"] = self._vars["ui.theme"].get()
        ui["opacity"] = round(self._vars["ui.opacity"].get(), 2)
        ui["font_size"] = self._vars["ui.font_size"].get()
        ui["animation_speed"] = round(self._vars["ui.animation_speed"].get(), 2)

        # 热键
        hk["shift"] = self._vars["hotkey.shift"].get()
        hk["ctrl"] = self._vars["hotkey.ctrl"].get()
        hk["alt"] = self._vars["hotkey.alt"].get()
        hk["key"] = self._vars["hotkey.key"].get().strip() or "m"

        # AI
        ai["enabled"] = self._vars["ai.enabled"].get()
        ai["api_base"] = self._vars["ai.api_base"].get().strip()
        ai["api_key"] = self._vars["ai.api_key"].get().strip()
        ai["model"] = self._vars["ai.model"].get().strip()

        # 剪贴板
        clip["monitor_enabled"] = self._vars["clipboard.monitor_enabled"].get()
        clip["min_length"] = self._vars["clipboard.min_length"].get()

        # 开机自启
        autostart_enabled = self._vars["autostart.enabled"].get()
        self.cfg.setdefault("autostart", {})["enabled"] = autostart_enabled
        set_autostart(autostart_enabled)

        # 右键菜单
        ctx_menu_enabled = self._vars["context_menu.enabled"].get()
        ctx["enabled"] = ctx_menu_enabled
        set_context_menu_enabled(ctx_menu_enabled)

        if self.on_save:
            self.on_save(self.cfg)

        self._close()

    def _reset_defaults(self):
        """恢复所有设置为默认值"""
        self._vars["ui.theme"].set("dark")
        self._vars["ui.opacity"].set(0.95)
        self._vars["ui.font_size"].set(13)
        self._vars["ui.animation_speed"].set(1.0)
        self._vars["hotkey.shift"].set(True)
        self._vars["hotkey.ctrl"].set(True)
        self._vars["hotkey.alt"].set(False)
        self._vars["hotkey.key"].set("m")
        self._vars["ai.enabled"].set(True)
        self._vars["ai.api_base"].set("https://token-plan-cn.xiaomimimo.com/v1")
        self._vars["ai.api_key"].set("tp-cr6615u5dv567yf4rrh1jti1cffpjuqrzvrqffru364ori7d")
        self._vars["ai.model"].set("mimo-v2.5")
        self._vars["clipboard.monitor_enabled"].set(False)
        self._vars["clipboard.min_length"].set(2)
        self._vars["autostart.enabled"].set(False)
        self._vars["context_menu.enabled"].set(False)
        if self.on_theme_change:
            self.on_theme_change("dark")

    def _close(self):
        if self.win:
            # 解绑滚轮
            try:
                self.win.unbind_all("<MouseWheel>")
            except Exception:
                pass
            self.win.destroy()
            self.win = None

    @property
    def is_open(self):
        return self.win is not None
