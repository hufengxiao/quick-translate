# Quick Translate 📖🔍

轻量级 Windows 查词翻译工具，模拟 macOS Spotlight 体验。

## ✨ 功能特性

- **全局快捷键** `Shift+Ctrl+M` 随时唤出
- **实时匹配** 输入即搜，毫秒级响应
- **本地词典** 66,818 词条牛津高阶英汉双解（第10版），离线可用
- **AI 翻译** 支持 OpenAI 兼容 API（按 Tab 触发）
- **透明度调节** 底部滑块自由调整窗口透明度
- **暗色主题** Catppuccin Mocha 配色，护眼舒适
- **零依赖** 仅需 Python + tkinter，无需安装第三方库

## 🚀 快速开始

```bash
# 直接运行
python main.py

# 或双击
start.bat
```

## ⌨️ 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Shift+Ctrl+M` | 唤出/隐藏窗口 |
| `↑↓` | 选择候选词 |
| `Enter` | 查看完整释义 |
| `Tab` | AI 翻译当前输入 |
| `Esc` | 关闭窗口 |

## ⚙️ 配置

首次运行后，在 `~/.quick-translate/config.json` 中配置：

```json
{
  "ai": {
    "enabled": true,
    "api_base": "https://api.openai.com/v1",
    "api_key": "sk-xxx",
    "model": "gpt-4o-mini"
  }
}
```

支持任何 OpenAI 兼容 API（如 DeepSeek、Ollama、vLLM 等）。

## 📁 项目结构

```
quick-translate/
├── main.py          # 入口
├── config.py        # 配置管理
├── hotkey.py        # 全局热键 (RegisterHotKey)
├── ui.py            # tkinter UI
├── dictionary.py    # 本地词典
├── translator.py    # AI 翻译引擎
├── start.bat        # Windows 启动脚本
└── data/dict/
    └── ecdict.json  # 牛津高阶英汉双解 (66,818 词)
```

## 🔧 扩展词典

替换 `data/dict/ecdict.json`，格式为 JSON 对象：

```json
{
  "word": "释义",
  "hello": "int. 你好"
}
```

## 📝 系统要求

- Windows 10/11
- Python 3.8+（含 tkinter）
