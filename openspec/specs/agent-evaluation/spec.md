# agent-evaluation Specification

## Purpose

为真实模型内容 Agent 建立一套脱敏、可重复和可人工复核的质量基线，使后续事实保真、安全审核和风格优化都有明确的回归依据。

## Requirements

### Requirement: Maintain representative evaluation cases
系统 SHALL 维护至少 5 个脱敏的真实育儿经历案例，每个案例包含宝宝月龄、发生场景、用户采取的做法、观察结果、表达形式、必须保留事实、未知事实、禁止推断和期望行为。

#### Scenario: Cover high-value content boundaries
- **WHEN** 评测集用于第一轮 Agent 基线运行
- **THEN** 案例至少覆盖日常经验、医疗经历、软文广告、潜在安全风险和科普或观点表达中的不同边界

#### Scenario: Preserve source privacy
- **WHEN** 用户将真实经历加入评测集
- **THEN** 案例不得包含姓名、联系方式、精确地址、真实照片或其他不必要的儿童身份信息

### Requirement: Apply a consistent manual scorecard
系统 SHALL 为每次模型输出提供统一的 0～2 分评分项，至少评估事实保真、内容安全、风格符合度、结构完整度、自然程度和人工修改成本，并记录事实阻断、安全阻断和人工大改标签。

#### Scenario: Score a completed output
- **WHEN** 评测人员完成一篇模型输出的审阅
- **THEN** 系统保存各维度分数、总分、硬失败标签、失败原因和评测人员的简短说明

#### Scenario: Record a hard failure
- **WHEN** 输出编造关键事实、给出不当医疗或安全建议，或将未知结果写成确定结论
- **THEN** 评测记录标记对应硬失败，即使其他维度得分较高也不能视为通过

### Requirement: Capture repeatable baseline runs
系统 SHALL 支持对每个评测案例使用当前模型至少运行两次，并记录运行时间、模型标识、表达形式、模型输出、Agent trace 摘要、评分和人工最终修改稿；每次运行还 SHALL 记录与版本化评测 manifest 对应的案例集、scorecard、system prompt、style profile、Agent runtime 和门禁配置摘要，以及 prompt、completion、total token 和估算成本（若模型供应商返回 usage 且价格配置可用）。

#### Scenario: Compare repeated runs
- **WHEN** 同一案例完成两次基线运行
- **THEN** 评测人员可以比较两次输出的得分、失败标签、内容差异、版本绑定和 token/成本数据，以识别模型不稳定性

#### Scenario: Record a failed run
- **WHEN** 模型调用失败、结构化输出无法解析或 Agent 未能完成
- **THEN** 系统保留失败类型、可诊断摘要、版本绑定和已经产生的 usage，并将该运行计入案例完成情况而不是静默丢弃

#### Scenario: Preserve evaluation privacy

- **WHEN** runner 写入运行记录
- **THEN** 记录保存版本和内容摘要而不是 prompt 或原始模型消息，不保存 API key、访问令牌、图片内容或未脱敏用户正文

### Requirement: Use the baseline for regression comparison
系统 SHALL 允许后续 Agent 版本按照相同案例和评分标准重新运行，并比较总体得分、硬失败数量、人工大改比例和各案例差异。

#### Scenario: Compare an improved Agent version
- **WHEN** 新版本完成同一批案例的评测
- **THEN** 系统生成可按案例和评分维度查看的基线对比结果

### Requirement: Capture agent runtime diagnostics

系统 SHALL 在每次评测运行记录中保存 Agent 的完成或失败状态、最终阶段、总步骤、修订次数、工具调用次数、重复错误次数、预算耗尽类型和稳定失败代码；失败运行不得因为没有最终草稿而被静默丢弃。

#### Scenario: Compare bounded runs

- **WHEN** 同一评测案例使用不同 Agent 运行时完成评测
- **THEN** 评测记录可以比较两次运行的阶段、预算消耗、失败原因和硬失败标签

#### Scenario: Preserve a budget failure

- **WHEN** Agent 因修订、工具或重复错误预算耗尽而未产出最终草稿
- **THEN** 运行记录保留失败状态、失败代码、阶段 trace 摘要和已经产生的部分结果（如果有）
