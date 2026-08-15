## MODIFIED Requirements

### Requirement: Block diagnosis and medication advice

系统 SHALL 结合生成内容、来源事实账本和育儿领域安全规则，识别疾病判断、症状推理、药物名称、剂量、疗程、医疗效果承诺及其他不可由来源支持的医疗结论，并阻止其作为普通经验笔记直接生成或导出；所有生成路径都必须产生包含声明审计的审核结果后才能进入可用状态。

#### Scenario: Common-care experience

- **WHEN** 用户描述感冒、发烧、尿布疹或湿疹相关的自身护理过程且不请求诊断或用药建议
- **THEN** 系统允许整理用户提供的事实，同时保留相关医疗不确定性和审核结果，将草稿标记为需要人工复核，不得在没有完整审核结果时标记为 `ready`

#### Scenario: Diagnosis or medication request

- **WHEN** 用户请求判断疾病、推荐药物或给出用量，或生成内容加入来源没有提供的诊断、医嘱、药名、剂量或疗程
- **THEN** 系统不生成具体诊断或用药方案，并显示需要咨询专业医疗人员的提示；包含 blocking 风险的草稿不得导出

### Requirement: Detect fabricated or exaggerated content

系统 SHALL 使用来源声明审计和育儿领域规则检查生成稿是否包含来源中不存在的关键经历、保证性效果、绝对化结论、未经验证的产品或发育功效、危险睡眠建议、虚构外部背书或制造焦虑的表达，并将检查结果纳入草稿状态和导出判断。

#### Scenario: Unsupported claim

- **WHEN** 生成稿声称某做法一定有效、某产品绝对安全、某睡眠方式可以照做，或加入用户来源没有提供的结果和细节
- **THEN** 系统记录 `unsupported` 声明及证据；危险建议、虚构关键经历和确定性安全结论至少标记为 blocking，草稿不能被视为已通过检查

#### Scenario: Uncertain claim

- **WHEN** 生成稿包含无法从来源确认的概括、因果关系、效果或外部背书，但尚未达到明确 blocking 条件
- **THEN** 系统将其标记为 `uncertain` 或 warning，草稿状态为 `needs_review`，并向用户展示可定位的审核原因

#### Scenario: Passed review

- **WHEN** 草稿已完成来源声明审计和安全审核，且没有 blocking 风险或 warning/uncertain 问题
- **THEN** 系统将草稿标记为 `ready`，并允许用户继续编辑和复制

#### Scenario: Warning review

- **WHEN** 草稿已完成来源声明审计和安全审核但存在 warning 或 uncertain 问题且没有 blocking 风险
- **THEN** 系统将草稿标记为 `needs_review`，向用户展示审核提示，并要求用户经过人工复核后再继续使用

### Requirement: Enforce review completion before readiness and export

系统 SHALL 将包含来源声明审计的审核结果作为草稿进入 `ready` 状态和导出的前置条件；审核结果缺失、事实审计缺失、审核结果过期或包含 blocking 风险时不得静默放行。

#### Scenario: Missing review result

- **WHEN** 生成、重写、字段重生成或保存后的草稿没有审核结果或没有本版本对应的声明审计
- **THEN** 系统不得将草稿标记为 `ready`，导出请求必须被拒绝或转为需要人工复核的结果

#### Scenario: Blocking review result

- **WHEN** 草稿审核结果包含 blocking 风险，或声明审计发现危险睡眠、医疗、产品安全或虚构关键经历
- **THEN** 系统将草稿标记为 `needs_review`，导出请求被拒绝，并返回可展示的风险原因和命中文本

#### Scenario: All generation paths use the same review contract

- **WHEN** 用户通过主生成、持久化生成、整篇风格重写、字段重生成或保存任一路径得到草稿
- **THEN** 系统使用相同的事实审计、审核状态语义和导出门禁，不因入口不同而绕过审核
