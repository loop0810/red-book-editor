## Why

Milestone 1 已经让事实审计和安全审核成为生成链路的可靠边界，但当前 Agent 仍主要依赖一个总步数上限。真实 baseline 已出现重复修订、`agent_max_steps` 和最终整理失败；现在需要把 Agent 从“自由循环”推进为可控、可诊断的有限状态工作流。

## What Changes

- 新增有序的 Agent 阶段：`collect_context`、`draft`、`critique`、`revise`、`safety_review`、`finalize`。
- 为每次运行增加独立的修订次数、工具调用次数、重复错误次数和阶段/总运行预算。
- 让服务端控制阶段转换，模型只负责阶段内的生成或判断，不能自行绕过安全审核或最终校验。
- 为运行结果增加明确的完成、失败和预算耗尽语义，并保留可展示的阶段 trace 与失败摘要。
- 在 Agent 评测记录中保存阶段、修订、工具调用、预算耗尽和失败原因，支持定位 `agent_max_steps` 等问题。
- 保持现有同步生成 API、结构化 NoteDraft、Fact Ledger、Claim Audit 和导出门禁语义不变。
- 本 change 第一阶段不包含 AgentRun 数据库持久化、SSE/WebSocket、取消恢复、Memory、RAG、MCP 或自动发布。

## Capabilities

### New Capabilities

- `agent-runtime-workflow`: 定义 Agent 阶段、运行预算、有限状态转换、失败语义和 trace 行为。

### Modified Capabilities

- `agent-evaluation`: 评测运行记录增加 Agent 阶段和预算相关的可诊断字段，并将预算耗尽和重复错误作为可比较的失败结果。

## Impact

- 服务端 `domain/agent.py`、内容工作流 styling agent、Agent trace 契约和相关测试。
- 评测 runner、运行记录 schema 和硬失败回归检查。
- Flutter 暂时只消费兼容的完成/失败 trace，不新增流式 UI。
- 不新增数据库表或 migration；本阶段只扩展内存运行结果与评测 JSON。
