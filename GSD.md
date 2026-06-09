# GSD — Quick Translate 持续优化

## 已完成
- [x] feat: MDX 原生词典支持 (300K 牛津词条)
- [x] feat: SQLite 缓存加速 MDX 查询
- [x] fix: preload 按常用短词优先加载
- [x] ui: 搜索/详情模式互斥显示

## 进行中
- [ ] fix: MDX pos 词性提取大部分返回空
- [ ] fix: history 去重应忽略大小写
- [ ] feat: 候选列表显示音标预览
- [ ] perf: MDX SQLite 加载移至后台线程
- [ ] fix: Escape 在详情模式应返回列表而非关闭窗口
- [ ] feat: 详情面板加"返回列表"按钮
- [ ] feat: 详情面板点击单词链接可跳转查询
- [ ] perf: 候选列表渲染优化（限制显示数量）
- [ ] fix: config 中 MDX 路径可配置
- [ ] feat: 双击候选词进入详情（而非触发 AI）
