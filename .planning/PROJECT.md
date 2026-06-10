# Quick Translate

## What This Is

Windows 桌面查词翻译工具，Spotlight 风格体验。按 Shift+Ctrl+M 唤出，输入即搜，选中即展示牛津高阶英汉双解完整释义。支持 AI 翻译兜底。

## Core Value

**毫秒级查词 + 牛津完整释义** — 用户按快捷键到看到释义必须 < 200ms，释义必须包含音标、词性、中英对照释义、例句。

## Requirements

### Validated

- ✓ 全局热键 Shift+Ctrl+M 唤出/隐藏
- ✓ 本地词典 66,818 词条（JSON 格式）
- ✓ MDX 原生词典 300,295 词条（牛津高阶第10版）
- ✓ SQLite 缓存加速 MDX 查询 (0.1ms)
- ✓ AI 翻译兜底（OpenAI 兼容 API）
- ✓ 系统托盘 + 右键菜单
- ✓ 暗色主题（Apple HIG 配色）
- ✓ 搜索/详情模式互斥显示

### Active

- [ ] 候选列表音标预览（已部分完成）
- [ ] 详情面板 ← 返回列表按钮
- [ ] Escape 详情→列表，列表→关闭
- [ ] MDX 后台加载不阻塞启动
- [ ] 剪贴板监听自动翻译
- [ ] PyInstaller 单文件 EXE 打包
- [ ] GitHub Actions CI/CD

### Out of Scope

- 多语言翻译（只做英汉）— 范围过大，保持专注
- 移动端/跨平台 — 仅 Windows
- 词典编辑功能 — 用户不需要
- 网络词典同步 — 隐私考虑，本地优先

## Context

- Python 3.10+ / tkinter 零依赖
- 牛津高阶第10版 MDX 词典文件在本地
- 用户偏好 Apple 风格 UX
- 已有 GitHub 仓库: hufengxiao/quick-translate

## Constraints

- **零依赖**: 仅 Python + tkinter，不引入 PyQt/Electron 等
- **Windows only**: 使用 Win32 API (RegisterHotKey, Shell_NotifyIcon, DWM)
- **离线优先**: 本地词典必须可用，AI 翻译为可选增强
- **启动速度**: 冷启动 < 3s

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| tkinter 而非 PyQt | 零依赖，Python 内置 | ✓ Good |
| MDX + SQLite 而非纯 JSON | 300K 词条完整内容 | ✓ Good |
| 搜索/详情模式互斥 | 避免界面拥挤 | ✓ Good |
| 后台加载 MDX | 不阻塞启动 | ✓ Good |

---
*Last updated: 2026-06-09 after GSD Core deployment*
