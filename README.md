# Quick Translate 📖🔍

轻量级 Windows 查词翻译工具，Spotlight 风格体验。Apple HIG 设计标准。

## ✨ 功能特性

- **全局快捷键** `Shift+Ctrl+M` 随时唤出
- **实时匹配** 输入即搜，选中即展示完整释义
- **本地词典** 66,818 词条牛津高阶英汉双解（第10版）
- **AI 翻译** 本地无结果时自动提示，Enter 一键翻译
- **有道词典** 本地无结果时自动查询有道词典 API
- **剪贴板监听** 复制英文自动弹出窗口查询（可关闭）
- **查词历史** 自动记录最近 50 条查询，唤出即显示
- **系统托盘** 最小化到托盘，右键菜单管理
- **透明度调节** 设置按钮可调 10%~90%，失焦自动变透明
- **窗口拖拽** 搜索栏、释义面板、顶部栏均可拖拽
- **剪贴板** 点击释义区域自动复制
- **暗色主题** Apple HIG 配色（深色模式）
- **流畅动画** 淡入/淡出/弹性缩放，60fps
- **零依赖** 仅需 Python + tkinter

## 🚀 快速开始

```bash
# 基础运行（无需额外依赖）
python main.py


# 或双击 start.bat
```

## ⚡ 性能指标

| 指标 | 改进前 | 改进后 |
|------|--------|--------|
| 精确查询 | ~50ms | < 1ms |
| 前缀搜索 | ~100ms | < 5ms |
| 启动时间 | ~500ms | ~1200ms (含 tkinter + 托盘 + 热键) |

## ⌨️ 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Shift+Ctrl+M` | 唤出/隐藏窗口 |
| `↑↓` | 选择候选词（选中即展示释义）|
| `Enter` | AI 翻译 |
| `Tab` | AI 翻译（兼容）|
| `Esc` | 关闭窗口 |

## ⚙️ 配置

首次运行自动生成 `~/.quick-translate/config.json`：

```json
{
  "clipboard": {
    "monitor_enabled": false,
    "min_length": 2,
    "auto_translate": false
  },
  "ai": {
    "enabled": true,
    "api_base": "https://api.openai.com/v1",
    "api_key": "sk-xxx",
    "model": "gpt-4o-mini"
  },
  "logging": { "level": "INFO", "file_enabled": true }
}
```

## 📁 项目结构

```
quick-translate/
├── main.py              # 入口
├── start.bat            # Windows 启动脚本
├── quicktranslate.spec  # PyInstaller 打包配置
├── src/
│   ├── core/
│   │   ├── dict/dictionary.py    # 词典门面类
│   │   ├── index/exact.py        # HashMap O(1)
│   │   ├── index/trie.py         # Trie O(m)
│   │   ├── index/router.py       # 查询路由器
│   │   ├── cache/lru.py          # LRU 缓存
│   │   └── lazy/loader.py        # 2阶段懒加载
│   ├── ui/
│   │   ├── spotlight.py          # Spotlight UI
│   │   ├── theme.py              # Apple HIG 主题
│   │   ├── animator.py           # 动画引擎
│   │   └── layout.py             # 8px 网格
│   ├── services/
│   │   ├── clipboard.py          # 剪贴板监听
│   │   └── dict_sources/sources.py # 多词典源
│   └── utils/
│       ├── config.py             # 配置管理
│       ├── errors.py             # 异常体系
│       └── logging.py            # 日志系统
├── hotkey.py            # 全局热键
├── translator.py        # AI 翻译
├── history.py           # 查词历史
├── tray.py              # 系统托盘
└── data/dict/ecdict.json # 66,818 词
```

## 📝 系统要求

- Windows 10/11
- Python 3.10+（含 tkinter）
- loguru（可选，自动回退到 stdlib logging）

## 📦 打包为 EXE

```bash
pip install pyinstaller
pyinstaller quicktranslate.spec
# 输出: dist/QuickTranslate.exe (~10MB)
```
