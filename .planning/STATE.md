# STATE.md — Quick Translate

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-09)

**Core value:** 毫秒级查词 + 牛津完整释义
**Current focus:** Phase 3 — Performance & Stability

## Current State

- **Phase:** 3 (Performance & Stability)
- **Milestone:** 1 (Production Ready)
- **Last shipped:** Phase 2 — MDX Integration

## What Works

- 全局热键 Shift+Ctrl+M
- 66K JSON 词典 + 300K MDX 牛津词典
- SQLite 缓存 (0.1ms 查询)
- 搜索/详情模式互斥
- AI 翻译兜底
- 暗色主题 Apple HIG

## Known Issues

- MDX 后台加载 ~8s（BKTree 构建慢）
- 候选列表超过 30 条时渲染略卡
- 窗口位置记忆偶尔不生效

## Next Actions

1. Trie/BKTree 索引持久化
2. 候选列表虚拟化
3. 启动 benchmark CI

---
*Updated: 2026-06-09*
