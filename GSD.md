# GSD — Quick Translate 持续优化

## 已完成
- [x] feat: MDX 原生词典支持 (300K 牛津词条)
- [x] feat: SQLite 缓存加速 MDX 查询
- [x] fix: preload 按常用短词优先加载
- [x] ui: 搜索/详情模式互斥显示
- [x] fix: MDX pos 词性提取正则修复
- [x] fix: history 去重已是大小写不敏感（无需修改）
- [x] feat: 候选列表显示音标预览
- [x] perf: MDX SQLite 加载移至后台线程
- [x] fix: Escape 在详情模式返回列表而非关闭窗口
- [x] feat: 详情面板加"← 返回列表"按钮
- [x] fix: 双击候选词进入详情（而非触发 AI）
- [x] perf: 候选列表限制 30 条避免渲染卡顿

## 待办
- [ ] feat: 详情面板点击单词链接可跳转查询
- [ ] fix: config 中 MDX 路径可配置
- [ ] feat: Tab 触发 AI 翻译（详情模式下）
- [ ] feat: 详情面板发音按钮（SAPI/PowerShell）
- [ ] perf: Trie/BKTree 索引持久化到磁盘
- [ ] feat: 多词典切换 UI（MDX/JSON）
- [ ] fix: 窗口位置记忆跨会话生效
- [ ] feat: 搜索结果按匹配度排序（exact > prefix > fuzzy）
