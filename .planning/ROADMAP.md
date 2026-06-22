# ROADMAP.md — Quick Translate

## Milestone 1: Production Ready ✅

### Phase 1: UI Polish ✅
**Status:** DONE
- [x] 搜索模式只显示候选列表
- [x] 详情模式只显示释义面板
- [x] Escape 详情→列表→关闭
- [x] ← 返回列表按钮
- [x] 候选列表音标预览
- [x] 双击进入详情

### Phase 2: MDX Integration ✅
**Status:** DONE
- [x] MDX 文件解析
- [x] SQLite 缓存
- [x] HTML→纯文本转换
- [x] 词性提取修复
- [x] 后台加载不阻塞启动

### Phase 3: Performance & Stability ✅
**Status:** DONE
- [x] bisect O(log n) 前缀搜索
- [x] SQLite PRAGMA 优化
- [x] 查询缓存
- [x] 启动 benchmark CI

### Phase 4: Feature Completion ✅
**Status:** DONE
- [x] 剪贴板监听自动翻译
- [x] PyInstaller 单文件 EXE
- [x] Inno Setup 安装程序
- [x] 自动更新检测
- [x] GitHub Actions CI/CD

### Phase 5: Polish & Ship ✅
**Status:** DONE
- [x] 高对比度主题
- [x] 新用户引导
- [x] 完整 README
- [x] 性能基准测试
- [x] v1.0 Release

---

## Milestone 2: Enhanced Experience

### Phase 6: Search Intelligence ✅
**Goal:** 搜索更智能，容错更强
**Status:** DONE

- [x] 拼写纠错：输入 "helllo" 自动建议 "hello"（编辑距离 ≤ 2）
- [x] 搜索历史优先：输入时优先显示历史查过的词
- [x] 模糊拼音搜索：输入拼音 "nihao" 能找到 "你好"
- [x] 搜索结果按相关度排序（exact > prefix > contains）
- [x] 候选列表显示词性标签（n. v. adj.）

### Phase 7: Word Management ✅
**Goal:** 生词本和收藏功能
**Status:** DONE

- [x] 生词本：一键收藏单词到生词本
- [x] 生词本导出：导出为 CSV/Anki 格式
- [x] 生词本复习：随机抽取生词测试
- [x] 星标词汇：重要单词加星标置顶
- [x] 查词统计：显示每日/每周查词数量

### Phase 8: UI Enhancements
**Goal:** 界面更精致，交互更流畅
**Status:** PLANNED

- [x] 设置面板：可视化设置（不再手动编辑 JSON）
- [x] 主题跟随系统：自动切换 dark/light
- [x] 窗口大小可拖拽调整
- [x] 字体大小可调（Ctrl+/-）
- [x] 动画速度可调
- [ ] 多显示器支持：窗口记忆屏幕位置

### Phase 9: Translation Quality
**Goal:** 翻译结果更丰富准确
**Status:** PLANNED

- [ ] 多 AI 模型支持：配置多个 API，自动切换
- [ ] 翻译缓存：相同查询不重复调用 API
- [ ] 翻译历史：保存 AI 翻译结果
- [ ] 词根分析：显示词根、前缀、后缀
- [ ] 近义词/反义词：显示相关词汇
- [ ] 常用搭配：显示词组搭配

### Phase 10: Distribution & Polish
**Goal:** 更好的分发和用户体验
**Status:** PLANNED

- [ ] 安装程序美化：自定义安装界面
- [ ] 开机自启选项
- [ ] 全局右键菜单：选中文字右键翻译
- [ ] 系统通知：更新提醒用系统通知
- [ ] 多语言界面：UI 支持英文/中文切换
- [ ] 崩溃报告：自动收集错误信息
