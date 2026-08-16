# domain-strategy-packs Specification

## Purpose

为内容生成提供可版本化的领域上下文、输入约束、质量规则和安全政策，使育儿只是第一个可替换领域，而不是散落在通用 Agent 和客户端流程中的固定分支。

## Requirements

### Requirement: Register a versioned domain strategy pack

系统 SHALL 为每个可用内容领域注册稳定的 `domain_id`、版本、展示名称、内容输入定义、质量规则和安全政策；账号和生成请求必须引用一个已启用的领域策略包。

#### Scenario: Use the parenting strategy pack
- **WHEN** 账号配置的领域为 `parenting` 且策略包版本有效
- **THEN** 内容生成使用育儿领域的补充字段、写作上下文和安全规则，但通用生成流程不需要分支到育儿专属实现

#### Scenario: Reject an unavailable domain
- **WHEN** 账号引用不存在、已停用或不兼容的领域策略包
- **THEN** 系统拒绝生成并返回明确的领域配置错误，不使用另一个领域作为静默回退

### Requirement: Extend content input by domain without changing the core brief

系统 SHALL 以通用内容主题、原始素材和可选领域上下文组成核心 `ContentBrief`，领域策略包可以声明补充字段和校验规则，但不得要求通用客户端为每个领域编写独立的生成主流程。

#### Scenario: Parenting-specific context is optional to the core flow
- **WHEN** 用户填写内容主题和原始素材，并补充宝宝月龄等育儿字段
- **THEN** 系统将月龄作为育儿领域上下文参与生成，同时核心主题和原始素材仍是内容事实与重心的主要来源

#### Scenario: A future domain uses the same generation boundary
- **WHEN** 账号切换到另一个有效领域并提交该领域定义的补充字段
- **THEN** 系统仍使用相同的“理解主题、组织角度、生成、质量检查、修订、返回草稿”边界，只替换领域上下文和策略

### Requirement: Keep domain policy separate from user-facing output

系统 SHALL 允许领域策略包提供内部质量和安全判断，但策略执行结果必须通过统一的用户结果投影转换；领域策略、规则名称、模型阶段和内部证据不得自动成为 C 端页面内容。

#### Scenario: Internal policy finds a low-confidence claim
- **WHEN** 领域策略包发现一条需要内部复核但不构成阻断的声明
- **THEN** 系统保留内部诊断供服务端、评测或授权调试使用，普通用户仍只看到可编辑的文案结果

#### Scenario: Policy blocks a dangerous result
- **WHEN** 领域策略包判定内容触发真实阻断风险
- **THEN** 系统返回与实际风险匹配的可行动用户提示，并阻止该结果进入可复制或导出状态
