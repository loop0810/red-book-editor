## Why

当前 Flutter 主生成接口与服务端持久化生成接口各自维护一套流程，导致生成后的草稿可能无法保存、账号栏目上下文没有生效，且真实模型生成结果可能在没有审核结果的情况下进入 `ready` 或导出状态。现在先收敛这条基础链路，才能在其上安全地增加事实账本、状态化 Agent 和更丰富的 AI 能力。

## What Changes

- 将生成、账号/栏目上下文加载、审核和草稿持久化收敛到同一个应用服务流程。
- 确保 Flutter 主生成接口创建可保存的 `NoteModel` 和初始草稿版本。
- 要求所有生成、风格重写和字段重生成路径经过统一审核；没有审核结果的草稿不得标记为 `ready` 或导出。
- 将 blocking 风险、warning 风险和审核状态正确映射到笔记状态与导出门禁。
- 在服务端 DTO、数据库内容、更新请求和 Flutter `NoteDraft` 之间完整保留 `style_form`。
- 将字段重生成改为字段级任务，只返回或更新用户请求的字段，不重新生成整篇文案作为内部实现依赖。
- 增加生成、保存、列表、重新打开和字段重生成的跨端/API 回归测试。

## Capabilities

### New Capabilities

无。本变更收敛并强化现有笔记创作和内容审核能力。

### Modified Capabilities

- `note-creation`：生成结果必须成为可保存、可恢复的草稿；生成时使用账号和栏目上下文；字段重生成必须保持其他字段和表达形式不变。
- `content-safety-review`：所有生成结果必须有审核状态；没有审核结果或存在 blocking 风险时不得进入 `ready` 或导出，warning 风险必须进入人工复核路径。

## Impact

- 服务端：`content_workflow`、`notes` 路由和应用服务、领域契约、持久化映射、审核流程及相关测试。
- Flutter：`NoteDraft`、API Client、编辑器字段重生成和恢复逻辑及相关测试。
- API 契约：生成响应、草稿保存/读取和字段重生成请求将补齐 `style_form` 与审核状态语义。
- 数据库：沿用现有 JSONB 内容和草稿版本结构；如需 schema 变化，必须通过 Alembic migration。
- 本变更不引入 RAG、MCP、多 Agent、自动发布、Fact Ledger 或持久化 AgentRun。
