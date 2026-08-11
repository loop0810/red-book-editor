## Purpose

为真实模型内容 Agent 建立一套脱敏、可重复和可人工复核的质量基线，使后续事实保真、安全审核和风格优化都有明确的回归依据。

## ADDED Requirements

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
系统 SHALL 支持对每个评测案例使用当前模型至少运行两次，并记录运行时间、模型标识、表达形式、模型输出、Agent trace 摘要、评分和人工最终修改稿。

#### Scenario: Compare repeated runs
- **WHEN** 同一案例完成两次基线运行
- **THEN** 评测人员可以比较两次输出的得分、失败标签和内容差异，以识别模型不稳定性

#### Scenario: Record a failed run
- **WHEN** 模型调用失败、结构化输出无法解析或 Agent 未能完成
- **THEN** 系统保留失败类型和可诊断的摘要，并将该运行计入案例完成情况而不是静默丢弃

### Requirement: Use the baseline for regression comparison
系统 SHALL 允许后续 Agent 版本按照相同案例和评分标准重新运行，并比较总体得分、硬失败数量、人工大改比例和各案例差异。

#### Scenario: Compare an improved Agent version
- **WHEN** 新版本完成同一批案例的评测
- **THEN** 系统生成可按案例和评分维度查看的基线对比结果
