# Phase 6: Search Intelligence

## Goal
搜索更智能，容错更强

## Tasks

### 6.1 拼写纠错
**Type:** code
**Description:** 输入错误拼写时自动建议正确单词（编辑距离 ≤ 2）
**Files:** `dictionary.py`, `ui.py`
**Acceptance:**
- 输入 "helllo" 候选列表显示 "hello"
- 输入 "wrold" 候选列表显示 "world"
- 纠错结果排在普通匹配之后
- 不影响正常搜索性能

### 6.2 搜索历史优先
**Type:** code
**Description:** 输入时优先显示历史查过的词
**Files:** `dictionary.py`, `history.py`
**Acceptance:**
- 输入 "hel" 时，历史中查过的 "hello" 排在最前
- 历史词用不同颜色或标记区分
- 无历史匹配时回退到正常搜索

### 6.3 搜索结果排序优化
**Type:** code
**Description:** 按匹配度排序：exact > prefix > contains
**Files:** `dictionary.py`
**Acceptance:**
- 精确匹配始终排第一
- 前缀匹配排第二
- 包含匹配排最后
- 同级按字母序

### 6.4 候选列表词性标签
**Type:** code
**Description:** 候选列表中显示词性缩写（n. v. adj.）
**Files:** `ui.py`, `dictionary.py`
**Acceptance:**
- 有词性的词显示标签（如 "run  v.  跑"）
- 词性标签用不同颜色
- 无词性时不显示

### 6.5 测试
**Type:** test
**Description:** 为所有搜索改进编写测试
**Files:** `ci_test.py`
**Acceptance:**
- 测试拼写纠错
- 测试历史优先
- 测试排序逻辑
- 所有测试通过

## Verification
- [ ] 所有 ci_test.py 测试通过
- [ ] 拼写纠错正确工作
- [ ] 搜索结果排序正确
- [ ] 性能无回退
- [ ] git push 成功
