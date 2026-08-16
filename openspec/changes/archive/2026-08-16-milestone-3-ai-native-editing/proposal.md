## Why

Milestone 2 已经让 AgentRun 可观察、可取消和可恢复，但编辑器仍把字段重生成结果直接覆盖到当前草稿，用户无法判断 AI 改了什么，也无法安全地接受或拒绝单条建议。现在需要把生成结果变成可比较、可审阅、可选择性采纳的编辑协作体验，同时把来源事实和审核问题定位到具体字段，降低用户无意覆盖真实修改或误用高风险文案的可能。

## What Changes

- 新增会话内的字段级 AI 建议模型，建议包含目标字段、候选值、生成时的基础内容摘要、Diff、审核结果和来源证据。
- **BREAKING** 将字段重生成 API 改为只返回目标字段的候选建议；生成完成后不自动覆盖用户当前编辑内容，仓库内 Flutter Client 与测试同步迁移到新响应契约。
- 在 Flutter 编辑器中增加 AI 初稿与当前内容的 Diff、当前内容与 AI 候选的 Diff，以及单条建议的采纳、拒绝和冲突处理。
- 采纳建议时只更新目标字段，并继续通过服务端保存和审核流程；拒绝建议不得改变当前草稿。
- 增加字段级来源事实展示和审核问题定位；第一版定位到字段和命中文本，不要求字符范围高亮。
- 补齐生成失败后的重试/继续运行入口，以及基于事件序号的 SSE 断线续读体验。
- 保持会话内建议语义：本 change 不持久化 pending suggestion，不增加 suggestion 数据库表；关闭编辑器后未采纳的建议可以丢失。
- 保持现有审核、状态和导出门禁；采纳操作不能绕过 blocking、warning、声明审计或当前版本审核。

## Capabilities

### New Capabilities

- `ai-editing-interactions`: 定义字段级 AI 候选建议、Diff、采纳/拒绝、冲突保护和会话内建议生命周期。

### Modified Capabilities

- `note-creation`: 增加用户参与式字段编辑、建议不覆盖用户内容、字段级 Diff 和失败运行恢复入口。
- `fact-ledger-and-claim-audit`: 增加审核发现与字段的稳定关联，以及编辑器展示来源证据和命中文本的要求。

## Impact

- 服务端领域契约、内容工作流字段重生成服务、审核 DTO、FastAPI 路由和相关单元/API 测试。
- Flutter `app_core` 的字段建议、Diff、字段审核映射和 AgentRun 恢复模型/API；`note_creation` 编辑器和生成页面交互。
- `docs/contracts/CONTENT_WORKFLOW_CONTRACT.md` 以及 OpenSpec 主规格。
- 本 change 不新增数据库表、不引入模型供应商、不改变现有同步生成 API 的主响应、不改变 PostgreSQL schema 或发布边界。
