## Why

Milestone 3 已支持当前编辑会话内的字段候选和基础 Diff，但关闭编辑器后未采纳候选会丢失，跨设备无法继续审阅；现有 Diff 也无法对正文和短文本提供稳定的精确片段定位。现在补齐这些能力，可以让“生成—审阅—采纳/拒绝”成为可恢复的编辑流程，同时保持用户编辑、事实审核和导出门禁不变。

## What Changes

- 将字段建议保存为与笔记绑定的、可审计的候选历史，支持按字段查看、恢复和明确采纳/拒绝状态。
- 为建议历史增加服务端 API、账号/笔记范围校验、过期基础摘要检查和数据库迁移；不保存 prompt、原始模型消息、密钥、访问令牌或图片内容。
- Flutter 编辑器打开笔记时加载未决和历史候选，关闭或换设备后仍可继续审阅；基础内容已变化时显示 stale/conflict，不静默覆盖。
- 将客户端 Diff 升级为可稳定定位的编辑片段：正文保留段落/句子语义边界并提供片段级字符范围，标题/封面提供字符片段，话题保持集合差异；不引入平台特定 HTML 标记。
- 保存、采纳和恢复仍必须经过完整草稿审核、状态计算和导出门禁。

## Capabilities

### New Capabilities

无。本 change 扩展现有 AI 编辑交互能力。

### Modified Capabilities

- `ai-editing-interactions`：将会话内候选扩展为笔记范围的可恢复建议历史，并将基础 Diff 扩展为可定位的精确编辑片段。

## Impact

- 服务端：领域契约、内容工作流路由/服务、SQLAlchemy model/repository、Alembic migration、建议历史 API 和集成测试。
- Flutter：`app_core` 建议模型/API/Diff 算法，以及 `note_creation` 编辑器历史列表、恢复、冲突和采纳交互。
- 共享契约与文档：更新内容工作流契约和 Milestone 3 修复记录；不接入 Memory、RAG、MCP 或自动发布。
