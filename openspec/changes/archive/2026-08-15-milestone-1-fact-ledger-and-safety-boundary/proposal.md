## Why

当前生成链路只能用关键字符串包含判断来源事实，审核也主要依赖不带来源上下文的固定关键词。这使模型可以把用户没有提供的经历、结果、产品功效或睡眠安全结论写成事实；首轮 baseline 的 10 次运行全部包含硬失败，说明“文案生成成功”不能代表内容可用。现在需要把来源事实、生成声明和安全审核连接起来，才能继续扩展 Agent 能力。

## What Changes

- 新增结构化 Fact Ledger，从 `SourceExperience` 提取可确认事实、观察结果、个人观点、未知信息和禁止推断边界。
- 新增 Claim Audit，对生成内容中的关键声明标记 `supported`、`uncertain` 或 `unsupported`，并保留可展示的证据和命中文本。
- 将事实审计和安全策略接入主生成、整篇重写、字段重生成和保存后的统一审核流程。
- 明确医疗、婴儿睡眠、产品安全、虚构经历、外部背书和绝对化结论的 warning/blocking 映射，并继续由服务端决定草稿状态和导出门禁。
- 扩展服务端、Flutter 和共享内容契约以传递结构化审核结果；客户端复用现有审核提示展示原因，不新增 Fact Ledger 编辑器。
- 使用现有 JSONB 的内容和审核快照保存结果，保持旧草稿读取兼容，不新增数据库表或 migration。
- 为现有 5 个脱敏 baseline 案例增加自动硬失败检查，并补充事实审计、安全审核、保存恢复和导出门禁测试。
- **不包含** AgentRun 持久化、取消恢复、流式事件、独立修订/工具预算、素材理解、Memory、RAG、MCP 或自动发布。

## Capabilities

### New Capabilities

- `fact-ledger-and-claim-audit`: 管理来源事实边界、生成声明审计、证据关联和审核快照。

### Modified Capabilities

- `content-safety-review`: 将来源声明审计、育儿领域安全规则和不确定性纳入草稿状态与导出门禁。

## Impact

- 服务端领域契约、内容工作流审核器、风格 Agent 最终校验和持久化 DTO 映射。
- 现有 `ReviewResult` API 结构及 Flutter `NoteDraft` 审核解析与展示。
- 现有 `notes.review`、草稿版本 JSONB 的序列化内容；预期无需 schema migration。
- baseline 评测运行后的自动硬失败检查和回归测试资料。
- `docs/contracts/CONTENT_WORKFLOW_CONTRACT.md`、路线图状态和 OpenSpec 主规格将同步更新。
