# Phase 3: Performance & Stability

## Goal
启动 < 2s，搜索无卡顿，内存 < 100MB

## Tasks

### 3.1 Trie 索引持久化
**Type:** code
**Description:** 将 Trie 和 BKTree 索引序列化到磁盘，下次启动直接加载跳过重建
**Acceptance:**
- 首次构建后保存到 .cache 文件
- 后续启动 < 500ms 加载完成
- 词典文件变更时自动重建
**Files:** `src/core/index/trie.py`, `src/core/index/bktree.py`, `src/core/dict/dictionary.py`

### 3.2 MDX SQLite 查询优化
**Type:** code
**Description:** 优化 SQLite 查询性能，添加 FTS5 全文索引
**Acceptance:**
- 前缀查询 < 0.05ms
- 模糊查询 (LIKE) 使用索引
- PRAGMA 优化已应用
**Files:** `src/core/dict/mdx_dict.py`

### 3.3 候选列表虚拟化
**Type:** code
**Description:** 只渲染可见区域的候选词，避免长列表卡顿
**Acceptance:**
- 1000+ 候选词无卡顿
- 滚动流畅 60fps
- 内存不随列表长度增长
**Files:** `ui.py`

### 3.4 启动 Benchmark CI
**Type:** test
**Description:** 添加启动时间基准测试，CI 中检测性能回退
**Acceptance:**
- ci_test.py 包含启动时间断言
- 冷启动 < 3s
- 热启动 < 1s
**Files:** `ci_test.py`

### 3.5 内存 Profiling
**Type:** test
**Description:** 测量并记录各组件内存占用
**Acceptance:**
- 输出各组件内存占用报告
- 总内存 < 100MB
- 识别并修复内存泄漏
**Files:** `src/utils/performance.py`

## Verification

- [ ] 所有 ci_test.py 测试通过
- [ ] 冷启动 < 3s
- [ ] 搜索延迟 < 50ms
- [ ] 内存 < 100MB
- [ ] git push 成功
