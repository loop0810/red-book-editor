# ai-editing-interactions Specification

## Purpose

让用户能够比较、审阅并选择性采纳 AI 对笔记字段的修改，同时保护当前人工编辑、来源事实关系和已有审核门禁，避免候选建议静默覆盖用户内容。

## Requirements

### Requirement: Keep field suggestions separate from the current draft

系统 SHALL 将标题、正文、话题和封面文案的局部生成结果表示为独立的 `FieldSuggestion`，包含目标字段、候选值、suggestion ID、生成时的字段和完整内容摘要、审核结果及来源证据；候选返回后不得自动覆盖当前草稿。

#### Scenario: Preserve a manual edit while a suggestion is pending

- **WHEN** 用户在字段候选生成前或生成后修改当前字段
- **THEN** 系统保留当前内容，待处理候选只显示为独立建议

### Requirement: Show distinct field Diff modes

系统 SHALL 在客户端区分 AI 初稿与当前草稿的编辑 Diff，以及当前草稿与 AI 候选的建议 Diff；正文按段落或句子优先比较后提供可定位的编辑片段，标题和封面文案提供字符范围，话题按集合比较，来源关系通过审核证据展示而不是伪装成普通文本 Diff。每个编辑片段 SHALL 标识新增、删除或未变化内容，并携带对应的 before/after 范围；服务端不返回 HTML 或平台特定 Diff 标记。

#### Scenario: Review a candidate with precise spans

- **WHEN** 用户打开待处理的字段候选
- **THEN** 系统明确展示当前值和 AI 建议值，标识新增、删除和未变化片段，并可将片段映射回对应的字段文本范围

### Requirement: Accept or reject without bypassing review

系统 SHALL 支持单条候选的采纳和拒绝。采纳只更新目标字段并移除该待处理候选；保存仍通过完整草稿审核，任何 warning、blocking、uncertain 或 unsupported 结果都不能绕过 `needs_review` 或导出门禁。

#### Scenario: Accept a candidate with a changed base

- **WHEN** 目标字段已经不同于候选生成时的基础值
- **THEN** 系统提示冲突，并要求用户明确保留当前值或使用候选，不得静默覆盖

### Requirement: Keep suggestions session-only

系统 SHALL 将待处理候选及其历史状态绑定到笔记和目标字段，而不是只保存在当前编辑会话；关闭页面或更换设备后，服务端仍可恢复候选历史。候选恢复和状态更新不得持久化 prompt、模型原始消息、图片内容、密钥或访问令牌。

#### Scenario: Reopen a saved draft

- **WHEN** 用户关闭编辑器后重新打开草稿
- **THEN** 系统恢复已保存草稿、审核快照和该笔记的候选历史；已采纳或拒绝的候选保持其状态，未决候选仍要求用户明确处理

#### Scenario: Keep a resolved candidate out of the pending queue

- **WHEN** 候选状态已经是 `accepted`、`rejected` 或 `stale`
- **THEN** 客户端不把它当作可直接采纳的待处理候选，但可以在历史列表中查看状态和 Diff

### Requirement: Persist and restore suggestion history

系统 SHALL 将字段建议保存为笔记范围内可查询的候选历史，记录目标字段、候选值、生成时的字段和完整内容摘要、审核快照、来源证据、创建时间和 `pending`、`accepted`、`rejected`、`stale` 状态；建议历史不得保存 prompt、模型原始消息、密钥、访问令牌或图片内容。

#### Scenario: Persist a generated candidate

- **WHEN** 用户为已保存笔记请求字段重生成
- **THEN** 服务端返回 `FieldSuggestion` 并持久化同一 `suggestion_id`，候选不会自动改写当前笔记

#### Scenario: Restore pending candidates on another session

- **WHEN** 用户从另一设备或重新打开编辑器读取笔记建议历史
- **THEN** 服务端返回该笔记的未决和历史候选；客户端可以继续审阅、拒绝或采纳，不依赖原编辑会话内存

#### Scenario: Mark a candidate stale after the base changes

- **WHEN** 当前笔记字段或完整内容摘要已经不同于候选生成时的基础摘要
- **THEN** 服务端将候选标记为 `stale` 或拒绝无条件采纳，客户端显示冲突并要求用户明确处理

#### Scenario: Resolve a candidate without silently changing the note

- **WHEN** 用户明确采纳或拒绝某条候选
- **THEN** 服务端只更新该候选的状态；笔记正文仍由客户端显式保存，并继续执行完整审核和导出门禁
