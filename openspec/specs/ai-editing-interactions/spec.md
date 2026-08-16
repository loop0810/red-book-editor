# ai-editing-interactions Specification

## Purpose

让用户能够比较、审阅并选择性采纳 AI 对笔记字段的修改，同时保护当前人工编辑和已有审核门禁。

## Requirements

### Requirement: Keep field suggestions separate from the current draft

系统 SHALL 将标题、正文、话题和封面文案的局部生成结果表示为独立的 `FieldSuggestion`，包含目标字段、候选值、suggestion ID、生成时的字段和完整内容摘要、审核结果及来源证据；候选返回后不得自动覆盖当前草稿。

#### Scenario: Preserve a manual edit while a suggestion is pending

- **WHEN** 用户在字段候选生成前或生成后修改当前字段
- **THEN** 系统保留当前内容，待处理候选只显示为独立建议

### Requirement: Show distinct field Diff modes

系统 SHALL 在客户端区分 AI 初稿与当前草稿的编辑 Diff，以及当前草稿与 AI 候选的建议 Diff；正文按段落或句子优先比较，短文本按片段比较，话题按集合比较，来源关系通过审核证据展示而不是伪装成普通文本 Diff。

#### Scenario: Review a candidate

- **WHEN** 用户打开待处理的字段候选
- **THEN** 系统明确展示当前值和 AI 建议值，并标识新增、删除和未变化内容

### Requirement: Accept or reject without bypassing review

系统 SHALL 支持单条候选的采纳和拒绝。采纳只更新目标字段并移除该待处理候选；保存仍通过完整草稿审核，任何 warning、blocking、uncertain 或 unsupported 结果都不能绕过 `needs_review` 或导出门禁。

#### Scenario: Accept a candidate with a changed base

- **WHEN** 目标字段已经不同于候选生成时的基础值
- **THEN** 系统提示冲突，并要求用户明确保留当前值或使用候选，不得静默覆盖

### Requirement: Keep suggestions session-only

系统 SHALL 只在当前编辑会话内保存待处理候选；关闭页面后可以丢弃未采纳候选，不得为其持久化用户正文、模型原始消息、图片内容、密钥或访问令牌。

#### Scenario: Reopen a saved draft

- **WHEN** 用户关闭编辑器后重新打开草稿
- **THEN** 系统恢复已保存草稿和审核快照，但不承诺恢复此前未采纳的会话候选
