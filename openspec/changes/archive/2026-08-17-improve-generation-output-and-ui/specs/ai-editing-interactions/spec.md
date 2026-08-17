## MODIFIED Requirements

### Requirement: Keep field suggestions separate from the current draft

系统 SHALL 将标题、正文、话题和封面文案的局部生成结果表示为独立的 `FieldSuggestion`，候选返回后不得自动覆盖当前草稿；候选的审核证据和历史状态属于服务端质量能力，不属于首次生成页面的默认信息区域。

#### Scenario: Preserve a manual edit while a suggestion is pending

- **WHEN** 用户在字段候选生成前或生成后修改当前字段
- **THEN** 系统保留当前内容，待处理候选只显示为独立建议，不能静默覆盖用户编辑

### Requirement: Keep detailed Diff and candidate history secondary

系统 SHALL 支持对候选执行精确的当前值/建议值比较，并保留版本和候选历史；但首次生成结果 SHALL 优先展示可编辑内容，Diff、候选历史、运行诊断和内部审核证据只能通过次级入口或内部工具访问。

#### Scenario: Open the primary result

- **WHEN** 用户首次进入生成结果页面
- **THEN** 页面展示标题、正文、话题、配图建议及主要编辑操作，不主动展开 Diff、候选历史或审核证据

#### Scenario: Review a candidate when explicitly requested

- **WHEN** 用户主动打开某个字段候选
- **THEN** 系统可以展示当前值与建议值的差异，并要求用户明确采纳或拒绝

### Requirement: Apply only real blocking policy to user readiness

系统 SHALL 支持单条候选的采纳和拒绝，采纳不绕过完整审核；用户可见的 `needs_review` 或导出阻断只能由当前领域策略判定的真实阻断问题触发，内部 warning、低置信度证据或自然改写不得默认阻止用户编辑和复制。

#### Scenario: Accept a candidate with a changed base

- **WHEN** 目标字段已经不同于候选生成时的基础值
- **THEN** 系统提示冲突，并要求用户明确保留当前值或使用候选，不得静默覆盖

#### Scenario: Accept a candidate with an ordinary paraphrase

- **WHEN** 候选只是对来源事实的自然中文改写，且没有新增关键事实或风险结论
- **THEN** 系统允许继续编辑，并不因内部不确定性自动显示无关的审核错误

### Requirement: Keep candidate persistence safe

系统 SHALL 将待处理候选及其历史状态绑定到笔记和目标字段，允许跨会话恢复；候选历史不得持久化 prompt、模型原始消息、图片内容、密钥、访问令牌或未脱敏用户正文。

#### Scenario: Restore a pending candidate

- **WHEN** 用户重新打开已保存草稿
- **THEN** 系统恢复未决候选的状态，用户可以主动审阅、拒绝或采纳，且不需要恢复原编辑会话内存
