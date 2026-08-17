## MODIFIED Requirements

### Requirement: Check account scope

系统 SHALL 根据账号所引用的领域策略包、账号定位和栏目上下文检查内容范围，而不把 0～2 岁育儿规则写成所有账号的通用边界；范围判断属于质量控制，不得在普通结果中展示内部规则名称。

#### Scenario: In-scope content
- **WHEN** 草稿符合当前账号领域、定位和栏目上下文
- **THEN** 系统允许进入编辑流程，不插入固定免责声明或无关领域提示

#### Scenario: Out-of-scope topic
- **WHEN** 草稿明显超出账号领域或账号明确边界
- **THEN** 系统返回与账号定位相关的简短调整提示，并允许用户回到主题或素材处修改

### Requirement: Block diagnosis and medication advice

系统 SHALL 由当前领域策略包决定需要阻断的诊断、用药或其他高风险建议；服务端必须阻止真实阻断结果直接复制或导出，但不得因为普通文本出现一个宽泛医疗词就向用户展示不相关的疾病/用药提示。

#### Scenario: Common-care experience
- **WHEN** 用户如实记录与健康相关的个人经历，但没有请求诊断或用药方案
- **THEN** 系统允许整理用户提供的事实；只有领域策略明确判定需要用户处理时才显示对应提示，不能显示泛化的“检查疾病、用药”文案

#### Scenario: Diagnosis or medication request
- **WHEN** 用户请求判断疾病、推荐药物或给出用量，或生成内容加入来源没有提供的具体诊断、药名、剂量或疗程
- **THEN** 系统不生成具体方案，返回与实际风险匹配的提示，并阻止该结果复制或导出

### Requirement: Detect fabricated or exaggerated content

系统 SHALL 使用来源审计和领域规则识别来源外关键经历、保证性效果、绝对化结论、危险建议、虚构背书或其他高风险表达；普通语言改写、标题重组和未达到阻断标准的内部不确定性不得自动成为 C 端错误提示。

#### Scenario: Unsupported high-risk claim
- **WHEN** 生成稿声称某做法一定有效、某产品绝对安全、某睡眠方式可以照做，或加入来源没有提供的关键经历
- **THEN** 系统记录内部证据并将其判定为阻断或领域要求的处理状态，用户只收到精确指向问题字段的可行动提示

#### Scenario: Natural paraphrase
- **WHEN** 生成内容用自然中文改写、压缩或重组用户提供的事实，但没有引入新的关键结果或风险结论
- **THEN** 系统不得仅因为无法逐字匹配就向用户展示“来源不支持”错误，也不得把该改写当作医疗风险

### Requirement: Enforce review completion before readiness and export

系统 SHALL 在服务端保留完整审核和版本指纹，以保障真实阻断问题不能绕过导出门禁；用户可见的 `ready`/`needs_review` 语义必须由领域策略和实际阻断结果决定，内部 warning 或低置信度证据不能默认阻止普通内容的编辑和复制。

#### Scenario: Missing internal review
- **WHEN** 生成、重写、字段重生成或保存后的草稿缺少当前版本所需的内部审核结果
- **THEN** 服务端不得将其作为已完成的安全结果持久化或导出，并向用户返回简短的“正在检查/请重试”类提示，而不是展示内部审计结构

#### Scenario: Blocking review result
- **WHEN** 当前领域审核包含真实 blocking 风险
- **THEN** 系统将草稿标记为需要处理，复制/导出被拒绝，并返回与实际风险匹配的原因和目标字段

#### Scenario: Ordinary content has no irrelevant warning
- **WHEN** 草稿不包含医疗、用药或其他领域阻断信号
- **THEN** 页面不显示疾病、用药或泛化审核提示，且用户可以继续编辑、复制和保存

#### Scenario: All generation paths use the same policy contract
- **WHEN** 用户通过主生成、持久化生成、整篇重写、字段重生成或保存任一路径得到草稿
- **THEN** 系统使用同一领域策略和内部审核语义，不因入口不同而绕过阻断门禁，也不因入口不同而额外泄漏内部诊断
