# ROADMAP.md — Quick Translate

## Milestone 1: Production Ready

### Phase 1: UI Polish ✅
**Goal:** 搜索/详情模式互斥，交互流畅
**Status:** DONE

- [x] 搜索模式只显示候选列表
- [x] 详情模式只显示释义面板
- [x] Escape 详情→列表→关闭
- [x] ← 返回列表按钮
- [x] 候选列表音标预览
- [x] 双击进入详情

### Phase 2: MDX Integration ✅
**Goal:** 直接读取欧路词典 MDX 文件，展示完整牛津释义
**Status:** DONE

- [x] MDX 文件解析 (mdict -x 导出)
- [x] SQLite 缓存 (0.1ms 查询)
- [x] HTML→纯文本转换 (音标+词性+释义+例句)
- [x] 词性提取修复
- [x] 后台加载不阻塞启动

### Phase 3: Performance & Stability ✅
**Goal:** 启动 < 2s，搜索无卡顿，内存 < 100MB
**Status:** DONE

- [ ] Trie/BKTree 索引持久化到磁盘（跳过重建）
- [ ] MDX SQLite WAL 模式优化
- [ ] 候选列表虚拟化（只渲染可见项）
- [ ] 内存 profiling + 优化
- [ ] 启动时间 benchmark CI

### Phase 4: Feature Completion
**Goal:** 剪贴板监听、打包分发
**Status:** PLANNED

- [ ] 剪贴板监听自动翻译（Win32 AddClipboardFormatListener）
- [ ] PyInstaller 单文件 EXE
- [ ] Inno Setup 安装程序
- [ ] 自动更新检测
- [ ] GitHub Actions CI/CD

### Phase 5: Polish & Ship
**Goal:** 达到苹果级产品标准
**Status:** PLANNED

- [ ] 高对比度主题
- [ ] 新用户引导
- [ ] 完整 README + 截图
- [ ] 性能基准测试
- [ ] v1.0 Release
