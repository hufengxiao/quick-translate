# Quick Translate — 项目交接文档

**更新时间**: 2026-06-09
**GitHub**: https://github.com/hufengxiao/quick-translate

---

## 项目简介

Windows 桌面查词翻译工具，Spotlight 风格体验。按 `Shift+Ctrl+M` 唤出，输入即搜，选中即展示牛津高阶英汉双解完整释义（音标、词性、中英对照释义、例句）。支持 AI 翻译兜底。

**核心价值**: 毫秒级查词 + 牛津完整释义

---

## 技术栈

- Python 3.10+ / tkinter（零外部依赖）
- Windows 10/11 专用（Win32 API: RegisterHotKey, Shell_NotifyIcon, DWM 圆角）
- MDX 原生词典（牛津高阶第10版，300K 词条）+ SQLite 缓存
- JSON 词典 fallback（66,818 词条）
- AI 翻译：OpenAI 兼容 API（默认 mimo-v2.5）

---

## 项目结构

```
quick-translate/
├── main.py              # 入口
├── start.bat            # Windows 启动脚本
├── ci_test.py           # 测试套件（10 项）
├── quicktranslate.spec  # PyInstaller 打包配置
│
├── config.py            # 旧版配置（dict 格式，main.py 使用）
├── dictionary.py        # 词典门面（MDX + JSON + bisect + 缓存）
├── translator.py        # AI 翻译（OpenAI 兼容 API，有 threading.Lock）
├── hotkey.py            # 全局热键（RegisterHotKey，有 Event 同步）
├── history.py           # 查词历史（大小写不敏感去重）
├── tray.py              # 系统托盘（纯 ctypes，HANDLE 类型修正）
│
├── ui.py                # Spotlight 风格 UI
│                         # 搜索/详情模式互斥
│                         # 候选列表带音标预览
│                         # 详情面板有 ← 返回列表 按钮
│                         # Escape: 详情→列表→关闭
│                         # 双击候选词进入详情（不触发 AI）
│
├── src/
│   ├── core/dict/
│   │   └── mdx_dict.py  # MDX 词典读取器（SQLite 缓存，HTML→文本）
│   ├── ui/
│   │   ├── theme.py     # Apple HIG 主题（dark/light/high_contrast）
│   │   ├── animator.py  # 动画引擎（fade/scale/elastic）
│   │   └── layout.py    # 8px 网格布局常量
│   ├── services/
│   │   ├── clipboard.py # 剪贴板监听（Win32 AddClipboardFormatListener）
│   │   └── dict_sources/sources.py  # 多词典源框架
│   └── utils/
│       ├── config.py    # Dataclass 配置 + 校验
│       ├── errors.py    # 统一异常体系
│       ├── logging.py   # Loguru + stdlib fallback
│       └── performance.py  # 性能监控
│
├── data/dict/
│   ├── ecdict.json                       # 66K JSON 词典
│   └── 牛津高阶第10版英汉双解V132/
│       ├── 牛津高阶第10版英汉双解V132.mdx   # 58MB MDX 文件
│       └── 牛津高阶第10版英汉双解V132.db    # SQLite 缓存（首次运行自动生成）
│
├── .planning/           # GSD Core 规划文件
│   ├── PROJECT.md       # 项目上下文
│   ├── ROADMAP.md       # 5 阶段路线图
│   ├── STATE.md         # 当前状态
│   └── phases/3/PLAN.md # Phase 3 详细计划
│
└── .hermes/             # GSD Core（67 个 skills，35+ agents）
    ├── skills/gsd/
    ├── agents/
    ├── hooks/
    └── gsd-core/
```

---

## 已完成的工作

### Phase 1: UI 重构 ✅
- 搜索/详情模式互斥显示（不再同时显示候选列表和释义）
- 候选列表带音标预览：`hello  /həˈləʊ/  释义...`
- 详情面板有 ← 返回列表 按钮
- Escape 键：详情模式→列表模式→关闭窗口
- 双击候选词进入详情（而非触发 AI）
- 候选列表限制 30 条避免渲染卡顿
- MDX SQLite 后台加载不阻塞启动

### Phase 2: MDX 原生词典 ✅
- 直接读取欧路词典 MDX 文件（58MB）
- 首次运行自动构建 SQLite 缓存（~5s）
- 后续查询 0.03ms（前缀）/ 5ms（精确+HTML→文本）
- 300,295 词条（牛津高阶第10版完整内容）
- HTML→纯文本：音标 + 词性 + 中英对照释义 + 例句
- 正则修复：POS 提取处理额外 HTML 属性 + 清理尾部逗号

### Phase 3: 性能优化 ✅
- JSON 词典前缀搜索：bisect O(log n)（从 O(n) 线性扫描改进）
- 查询缓存（200 条 LRU）
- SQLite PRAGMA 优化：WAL + mmap 256MB + MEMORY temp + NORMAL sync
- 范围查询前缀搜索（3x faster than LIKE）
- 启动 Benchmark CI：ci_test.py 包含性能断言

### 已修复的 Bug
- hide() 快速切换死锁 → _visible 立即置位
- 后台线程重建索引与主线程搜索冲突 → 原子替换
- translator.py _busy 竞态 → threading.Lock
- hotkey.py _thread_id 未就绪 → Event.wait
- MDX pos 词性提取正则修复
- preload 排序策略：常用短词优先（按长度+字母序）
- remaining_keys 集合差集计算修复

---

## 当前性能指标

| 指标 | 数值 |
|------|------|
| JSON dict startup | 368ms |
| MDX SQLite load | 14ms |
| MDX exact lookup | 5.28ms |
| MDX prefix search | 0.03ms |
| MDX miss lookup | 0.005ms |
| ci_test.py | 10/10 PASS |

---

## GSD Core 部署状态

GSD Core v1.4.3 已安装到 `.hermes/` 目录。

```
npx @opengsd/gsd-core --hermes --local
```

已安装：
- 67 个 skills（plan-phase, execute-phase, verify-work, ship 等）
- 35+ 个专业子代理（planner, executor, verifier, debugger 等）
- 16 个 hooks（commit 校验、上下文监控、安全扫描等）

规划文件在 `.planning/`：
- PROJECT.md — 项目上下文
- ROADMAP.md — 5 阶段路线图
- STATE.md — 当前状态

---

## ROADMAP

| Phase | 名称 | 状态 |
|-------|------|------|
| 1 | UI 重构 | ✅ DONE |
| 2 | MDX 原生词典 | ✅ DONE |
| 3 | 性能优化 | ✅ DONE |
| 4 | 功能完善 | 待做 |
| 5 | 打磨发布 | 待做 |

---

## Phase 4 待做任务

1. **剪贴板监听自动翻译**
   - 已有 `src/services/clipboard.py`（Win32 AddClipboardFormatListener）
   - 需要集成到 main.py，配置开关 `clipboard.monitor_enabled`

2. **PyInstaller 单文件 EXE**
   - 已有 `quicktranslate.spec`
   - 需要测试打包流程，排除不需要的模块

3. **GitHub Actions CI/CD**
   - 已有 `.github/workflows/build.yml`
   - 需要验证 CI 流程是否正常

4. **config 中 MDX 路径可配置**
   - 当前 MDX 路径硬编码在 main.py 中
   - 应改为 config.json 中的 `dictionary.mdx_path` 字段

---

## Phase 5 待做任务

1. 高对比度主题（已有 theme.py 中的 HIGH_CONTRAST 定义）
2. 新用户引导
3. 完整 README + 截图
4. 性能基准测试
5. v1.0 Release

---

## 开发规范

- 提交格式: `type: description`（feat/fix/perf/refactor/chore）
- 测试: `python ci_test.py`（10 项测试）
- 分支: master（不要创建新分支）
- 推送: 每次提交后 `git push`

---

## 已知问题

- MDX 首次构建 SQLite 需要 ~5s（后续启动 14ms）
- BKTree 模糊搜索在 src/core/ 中有实现但当前架构未使用（main.py 用根目录模块）
- 旧版 src/core/ 模块（exact.py, trie.py, bktree.py, router.py）与当前 dictionary.py 是两套架构，未完全整合
- .gitignore 已排除 MDX 和 SQLite 文件（太大不能提交到 GitHub）

---

## 用户偏好

- 功能不好用就直接删掉（如 TTS 发音），不要保留半成品
- 偏好 Apple 风格 UX
- 中文交流
- 希望持续优化，用 GSD Core 驱动开发
