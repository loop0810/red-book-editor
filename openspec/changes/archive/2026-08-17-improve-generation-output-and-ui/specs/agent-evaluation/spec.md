## MODIFIED Requirements

### Requirement: Maintain representative domain-aware evaluation cases

系统 SHALL 维护可脱敏、可重复的内容评测案例；案例至少包含领域标识、明确内容重心、原始素材、账号定位/表达风格、必须保留事实、未知事实、禁止推断和期望行为。第一阶段至少包含 5 个育儿案例，但评测契约不得把育儿字段写成所有领域的必填项。

#### Scenario: Cover focus and domain boundaries

- **WHEN** 评测集用于第一轮 Content Agent 基线运行
- **THEN** 案例至少覆盖日常经验、医疗或高风险请求、软文/产品表达、潜在安全风险和科普或观点表达，并包含一个“主题与限制条件容易混淆”的重心案例

#### Scenario: Preserve source privacy

- **WHEN** 用户真实素材被加入评测集
- **THEN** 案例不得包含姓名、联系方式、精确地址、真实照片或其他不必要的儿童身份信息

### Requirement: Score product usefulness before internal observability

系统 SHALL 为每次模型输出提供统一的 0～2 分评分项，至少评估主题重心、账号/风格符合度、事实保真、内容安全、结构完整度、自然程度、用户价值和人工修改成本；Agent trace 和运行诊断只作为内部解释与回归证据，不作为 C 端价值指标。

#### Scenario: Score a completed output

- **WHEN** 评测人员完成一篇模型输出的审阅
- **THEN** 系统保存各维度分数、总分、硬失败标签、失败原因、人工修改成本和简短说明，并可以识别标题是否围绕用户主题

#### Scenario: Record a hard failure

- **WHEN** 输出偏离核心主题、编造关键事实、给出不当医疗/安全建议，或把未知结果写成确定结论
- **THEN** 评测记录标记对应硬失败，即使 Agent trace 完整或其他维度得分较高也不能视为通过

### Requirement: Capture repeatable internal baseline runs

系统 SHALL 支持对每个评测案例使用当前模型至少运行两次，并记录模型标识、表达形式、结构化输出、内部 Agent 诊断摘要、评分和人工最终修改稿；每次运行还 SHALL 绑定版本化评测 manifest、领域策略包版本和门禁配置摘要，不保存 prompt、模型原始消息、API key、访问令牌、图片内容或未脱敏用户正文。

#### Scenario: Compare repeated runs

- **WHEN** 同一案例完成两次基线运行
- **THEN** 评测人员可以比较两次输出的主题重心、风格/领域适配、得分、失败标签、内容差异以及内部运行诊断

### Requirement: Use the baseline for regression comparison

系统 SHALL 允许后续 Content Agent 和领域策略包版本按照相同案例和评分标准重新运行，并比较总体得分、主题偏移率、硬失败数量、人工大改比例、用户价值和各案例差异。

#### Scenario: Compare an improved domain strategy

- **WHEN** 新版本完成同一批案例的评测
- **THEN** 系统生成按领域、案例和评分维度查看的基线对比结果，同时保留内部运行失败原因
