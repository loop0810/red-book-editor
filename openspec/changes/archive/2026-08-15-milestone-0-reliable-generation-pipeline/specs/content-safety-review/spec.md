## MODIFIED Requirements

### Requirement: Block diagnosis and medication advice

系统 SHALL 识别疾病判断、症状推理、药物名称、剂量、疗程和医疗效果承诺等内容，并阻止其作为普通经验笔记直接生成或导出；所有生成路径都必须产生审核结果后才能进入可用状态。

#### Scenario: Common-care experience

- **WHEN** 用户描述感冒、发烧、尿布疹或湿疹相关的自身护理过程且不请求诊断或用药建议
- **THEN** 系统允许整理用户提供的事实，同时将草稿标记为需要人工复核，不得在没有审核结果时标记为 `ready`

#### Scenario: Diagnosis or medication request

- **WHEN** 用户请求判断疾病、推荐药物或给出用量
- **THEN** 系统不生成具体诊断或用药方案，并显示需要咨询专业医疗人员的提示；包含 blocking 风险的草稿不得导出

### Requirement: Detect fabricated or exaggerated content

系统 SHALL 检查生成稿是否包含来源中不存在的关键经历、保证性效果、绝对化结论或制造焦虑的表达，并将检查结果纳入草稿状态和导出判断。

#### Scenario: Unsupported claim

- **WHEN** 生成稿声称某做法一定有效，但用户来源没有提供该结果
- **THEN** 系统标记该问题并将草稿置于需要人工复核状态，不将其视为已通过检查

#### Scenario: Passed review

- **WHEN** 草稿已完成审核且没有 blocking 风险或 warning 问题
- **THEN** 系统将草稿标记为 `ready`，并允许用户继续编辑和复制

#### Scenario: Warning review

- **WHEN** 草稿已完成审核但存在 warning 问题且没有 blocking 风险
- **THEN** 系统将草稿标记为 `needs_review`，向用户展示审核提示，并要求用户经过人工复核后再继续使用

## ADDED Requirements

### Requirement: Enforce review completion before readiness and export

系统 SHALL 将审核结果作为草稿进入 `ready` 状态和导出的前置条件；审核结果缺失、过期或包含 blocking 风险时不得静默放行。

#### Scenario: Missing review result

- **WHEN** 生成、重写、字段重生成或保存后的草稿没有审核结果
- **THEN** 系统不得将草稿标记为 `ready`，导出请求必须被拒绝或转为需要人工复核的结果

#### Scenario: Blocking review result

- **WHEN** 草稿审核结果包含 blocking 风险
- **THEN** 系统将草稿标记为 `needs_review`，导出请求被拒绝，并返回可展示的风险原因

#### Scenario: All generation paths use the same review contract

- **WHEN** 用户通过主生成、持久化生成、整篇风格重写或字段重生成任一路径得到草稿
- **THEN** 系统使用相同的审核状态语义和导出门禁，不因入口不同而绕过审核
