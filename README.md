# Quick Translate

**轻量级 Windows 查词翻译工具，Spotlight 风格体验。**

按 `Shift+Ctrl+M` 唤出，输入即搜，选中即展示牛津高阶英汉双解完整释义。

## 功能特性

| 功能 | 说明 |
|------|------|
| 全局热键 | `Shift+Ctrl+M` 随时唤出/隐藏 |
| 牛津词典 | 300,295 词条，音标+词性+中英释义+例句 |
| AI 翻译 | 本地无结果时 Enter 一键 AI 翻译 |
| 剪贴板监听 | 复制英文自动弹窗查询 |
| 暗色主题 | Apple HIG 配色，支持高对比度 |
| 系统托盘 | 最小化到托盘，右键菜单 |
| 自动更新 | 启动时检查 GitHub Releases |
| 零依赖 | 仅需 Python + tkinter |

## 快速开始

```bash
# 方式一：直接运行
python main.py

# 方式二：双击
start.bat

# 方式三：打包为 EXE
pip install pyinstaller
pyinstaller quicktranslate.spec --noconfirm
dist/QuickTranslate.exe
```

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Shift+Ctrl+M` | 唤出/隐藏窗口 |
| `↑↓` | 选择候选词 |
| `Enter` | 查看详情 / AI 翻译 |
| `Tab` | AI 翻译 |
| `Esc` | 详情→列表→关闭 |
| 点击释义 | 复制到剪贴板 |

## 配置

首次运行自动生成 `~/.quick-translate/config.json`：

```json
{
  "hotkey": { "shift": true, "ctrl": true, "alt": false, "key": "m" },
  "ui": {
    "width": 340, "height": 480, "opacity": 0.95,
    "theme": "dark",
    "font_size": 13
  },
  "ai": {
    "enabled": true,
    "api_base": "https://api.openai.com/v1",
    "api_key": "sk-xxx",
    "model": "gpt-4o-mini"
  },
  "clipboard": {
    "monitor_enabled": false,
    "min_length": 2
  }
}
```

### 主题切换

在 `config.json` 中设置 `ui.theme`：
- `dark` — 暗色主题（默认）
- `light` — 亮色主题
- `high_contrast` — 高对比度主题

## 词典

### 内置 JSON 词典
- 66,818 词条
- 快速前缀搜索（bisect O(log n)）

### MDX 原生词典（牛津高阶第10版）
- 300,295 词条
- 完整内容：音标、词性、中英对照释义、例句
- SQLite 缓存，查询 0.03ms
- 首次运行自动构建缓存（~5s）

**使用方式**：将欧路词典的 MDX 文件放到 `data/dict/` 目录，程序自动检测。

## 项目结构

```
quick-translate/
├── main.py              # 入口
├── dictionary.py        # 词典引擎（MDX + JSON + bisect）
├── ui.py                # Spotlight 风格 UI
├── styles.py            # 设计系统（主题、字体、间距）
├── animations.py        # 动画引擎
├── updater.py           # 自动更新检测
├── hotkey.py            # 全局热键
├── translator.py        # AI 翻译
├── history.py           # 查词历史
├── tray.py              # 系统托盘
├── config.py            # 配置管理
├── ci_test.py           # 测试套件
├── loop.py              # Loop Engineering 自动开发循环
├── quicktranslate.spec  # PyInstaller 打包配置
├── quicktranslate.iss   # Inno Setup 安装程序
└── data/dict/           # 词典文件
```

## 开发

```bash
# 运行测试
python ci_test.py

# 查看项目进度
python loop.py --status

# PyInstaller 打包
pyinstaller quicktranslate.spec --noconfirm

# Inno Setup 安装程序
# 打开 quicktranslate.iss 编译
```

## 系统要求

- Windows 10/11
- Python 3.10+（含 tkinter）

## License

MIT
