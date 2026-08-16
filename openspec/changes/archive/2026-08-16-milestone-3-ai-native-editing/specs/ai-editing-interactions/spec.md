## Purpose

让用户能够理解、比较和选择性采纳 AI 对笔记字段的修改，同时保护已经产生的人工编辑，并在会话内保留可审阅的候选建议。

## ADDED Requirements

### Requirement: Keep AI field suggestions separate from the current draft

系统 SHALL 将字段重生成结果表示为独立的候选建议，而不是自动替换当前草稿；候选建议至少包含笔记标识、目标字段、候选值、生成时的基础字段摘要、当前建议状态和与当前值的可比较信息。

#### Scenario: Generate a title suggestion

- **WHEN** 用户请求重新生成标题
- **THEN** 系统返回只针对标题的候选建议，正文、话题、封面文案和当前草稿内容保持不变

#### Scenario: Preserve a manual edit while a suggestion is pending

- **WHEN** 用户在 AI 候选建议返回前或返回后修改当前字段
- **THEN** 系统保留用户当前内容，候选建议不会自动覆盖该内容

### Requirement: Show distinct comparison modes

系统 SHALL 支持区分 AI 初稿与当前草稿的编辑 Diff，以及当前草稿与 AI 候选建议的建议 Diff；来源事实关系不得被伪装成普通文本 Diff。

#### Scenario: Review changes made by the user

- **WHEN** 用户查看一个曾经生成过且已经被编辑的字段
- **THEN** 系统展示 AI 初稿与当前字段之间的新增、删除或未变化内容

#### Scenario: Review an AI candidate

- **WHEN** 用户打开待采纳的字段建议
- **THEN** 系统展示当前字段与候选字段之间的差异，并明确哪一侧是当前内容、哪一侧是 AI 建议

### Requirement: Accept or reject a suggestion without bypassing review

系统 SHALL 允许用户采纳或拒绝单条字段建议；采纳只更新目标字段并触发当前草稿的统一审核，拒绝不得改变当前草稿，任何采纳操作都不得绕过风险状态或导出门禁。

#### Scenario: Accept an unchanged-base suggestion

- **WHEN** 用户采纳建议且目标字段仍与建议生成时的基础内容一致
- **THEN** 系统只将候选值合并到目标字段，并保留其他字段、来源事实和表达形式

#### Scenario: Reject a suggestion

- **WHEN** 用户拒绝待采纳建议
- **THEN** 系统移除该建议，当前字段和其他草稿内容保持不变

#### Scenario: Accept a suggestion with a conflict

- **WHEN** 用户采纳建议但目标字段已经发生了不同于建议基础内容的修改
- **THEN** 系统不得静默覆盖当前内容，而是提示冲突并要求用户明确选择保留当前内容、查看 Diff 或使用候选值

#### Scenario: Accept a risky suggestion

- **WHEN** 候选值或合并后的完整草稿包含 warning、blocking 或未被来源支持的声明
- **THEN** 系统保留对应审核结果并阻止草稿绕过 `needs_review` 和导出门禁

### Requirement: Keep pending suggestions bounded to the editing session

系统 SHALL 在当前编辑会话内保存待处理建议，并允许页面关闭后丢弃未采纳建议；系统不得为待处理建议持久化用户正文、模型原始消息、图片内容、密钥或访问令牌。

#### Scenario: Reopen a note after closing the editor

- **WHEN** 用户关闭编辑器后重新打开笔记
- **THEN** 系统恢复已保存的当前草稿和审核结果，但不承诺恢复此前未采纳的会话内建议
