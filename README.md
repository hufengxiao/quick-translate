# Quick Translate 📖🔍

轻量级 Windows 查词翻译工具，Spotlight 风格体验。

## ✨ 功能特性

- **全局快捷键** `Shift+Ctrl+M` 随时唤出
- **实时匹配** 输入即搜，选中即展示完整释义
- **本地词典** 66,818 词条牛津高阶英汉双解（第10版）
- **AI 翻译** 本地无结果时自动提示，Enter 一键翻译
- **查词历史** 自动记录最近 50 条查询，唤出即显示
- **系统托盘** 最小化到托盘，右键菜单管理
- **透明度调节** 设置按钮可调 10%~90%，失焦自动变透明
- **窗口拖拽** 搜索栏、释义面板、顶部栏均可拖拽
- **剪贴板** 点击释义区域自动复制
- **暗色主题** Catppuccin Mocha 配色
- **零依赖** 仅需 Python + tkinter

## 🚀 快速开始

```bash
python main.py
# 或双击 start.bat
```

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
  "ai": {
    "api_base": "https://api.openai.com/v1",
    "api_key": "sk-xxx",
    "model": "gpt-4o-mini"
  }
}
```

支持任何 OpenAI 兼容 API（DeepSeek、Ollama、mimo 等）。

## 📁 项目结构

```
quick-translate/
├── main.py          # 入口
├── config.py        # 配置管理
├── hotkey.py        # 全局热键 (RegisterHotKey)
├── ui.py            # Spotlight 风格 UI
├── dictionary.py    # 本地词典查询
├── translator.py    # AI 翻译引擎
├── history.py       # 查词历史记录
├── tray.py          # 系统托盘图标
├── start.bat        # Windows 启动脚本
└── data/dict/
    └── ecdict.json  # 牛津高阶英汉双解 (66,818 词)
```

## 📝 系统要求

- Windows 10/11
- Python 3.8+（含 tkinter）
