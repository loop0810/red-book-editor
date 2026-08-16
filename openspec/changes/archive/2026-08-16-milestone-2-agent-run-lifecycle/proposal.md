## Why

Milestone 2 第一片已经让 Agent 在单次请求内具备阶段、预算和失败诊断，但运行结果仍然只存在于同步 HTTP 请求中；长耗时运行无法取消，服务端重启后也无法识别或恢复未完成任务。现在需要补齐一个可持久化、可观察、可协作的 AgentRun 生命周期，为 Flutter 的阶段进度体验提供稳定接口。

## What Changes

- 新增异步 AgentRun API：创建运行、查询状态、读取 SSE 阶段事件、请求取消和恢复失败/中断运行。
- 新增 AgentRun 和 AgentRunEvent 持久化模型，保存运行引用、状态、阶段、诊断、失败原因和有序的安全事件摘要，不保存完整 prompt、模型消息或用户正文。
- 让 AgentRuntime 在每次阶段/工具/模型事件后发出有序事件，并在网关调用和工具执行前检查取消请求。
- 服务端启动时识别遗留的 `running` 运行并标记为 `interrupted`；恢复从已持久化的笔记输入重新执行，并增加恢复次数，避免伪装成断点续跑。
- Flutter app_core 增加 AgentRun 状态、事件和取消/恢复 API 模型；笔记创建流程可以订阅阶段事件并展示运行状态。
- 保留现有同步生成、审核、Fact Ledger、NoteStatus 和导出门禁语义；不引入新的模型供应商或自动发布能力。

## Capabilities

### New Capabilities

- `agent-run-lifecycle`: 定义 AgentRun 持久化、生命周期、取消/恢复、阶段事件和 SSE API。

### Modified Capabilities

- `agent-runtime-workflow`: 增加运行取消协作和有序事件发射要求。

## Impact

- 服务端领域 Runtime、内容工作流 application service、AgentRun 模块、SQLAlchemy 模型、Alembic migration、FastAPI 路由和应用启动生命周期。
- Flutter `app_core` API client/models，以及 `note_creation` 运行状态展示。
- `docs/contracts/CONTENT_WORKFLOW_CONTRACT.md`、OpenSpec 主 spec、集成测试和数据库测试夹具。
- 不新增第三方编排框架；SSE 使用现有 FastAPI/Starlette 能力，事件由 PostgreSQL 持久化支持断线后的游标读取。
