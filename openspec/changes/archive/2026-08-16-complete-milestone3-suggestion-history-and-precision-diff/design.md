## Context

当前 `/api/v1/notes/regenerate-field` 只在内存中生成并返回 `FieldSuggestion`，Flutter 通过 `EditorSessionState.pendingSuggestions` 保存候选；关闭编辑器后候选会丢失。服务端已有 `NoteModel`、草稿版本和字段/内容 digest，可以在不保存模型原始消息的前提下增加笔记范围的候选记录。

现有客户端 Diff 已按字段选择列表、段落/句子或字符做比较，但 `DiffSegment` 只有 kind 和 text，不能稳定表示片段在 before/after 文本中的范围。该 change 继续由客户端生成展示 Diff，服务端只保存候选和审核元数据。

## Goals / Non-Goals

**Goals:**

- 为已保存笔记持久化字段候选及其状态，支持重新打开和跨设备读取。
- 在候选生成基础变化时返回/展示 `stale` 或冲突状态，采纳和拒绝状态可审计且不直接改写笔记。
- 为客户端 Diff 增加 before/after 范围信息，保留话题集合 Diff 和安全审核证据展示。
- 通过 Alembic 演进数据库，保持旧客户端读取 `FieldSuggestion` 时的兼容性。

**Non-Goals:**

- 不实现用户账号认证或跨账号权限系统；继续沿用现有 note/account 归属检查边界。
- 不保存 prompt、模型原始消息、完整 Agent trace、图片二进制、密钥或访问令牌。
- 不实现自动采纳、自动发布、Memory、RAG、MCP 或平台特定富文本标记。
- 不把 Diff 片段当作服务端可执行 patch；保存仍提交完整草稿并重新审核。

## Decisions

### 1. 使用独立的 `field_suggestions` 表

新增表保存 `suggestion_id`、`note_id`、`account_id`、字段、候选值 JSONB、基础字段/内容 digest、审核 JSONB、来源证据、状态和时间戳，并为 note/status/created_at 建索引。

选择独立表而不是把候选塞入 `notes.content` 或 `draft_versions`，是因为候选有独立生命周期、需要按状态查询和跨设备恢复；这样也不会把未采纳候选混入正式草稿版本。删除笔记时通过外键级联删除候选。

### 2. 生成与状态更新分离

内容工作流服务继续只负责生成和审核 `FieldSuggestionDto`，由 API 层通过 repository 持久化生成结果。新增按 note 查询候选历史和更新候选状态的端点；状态更新只改变候选记录，不改变 NoteModel。接受时客户端先处理本地草稿并显式保存，随后同步候选状态。

候选查询会将当前笔记的字段/内容 digest 与候选基础 digest 比较；不匹配的 pending 候选在响应中标记为 `stale`，避免旧客户端或另一设备无条件覆盖新编辑。

### 3. 以状态和 digest 兼容旧客户端

`FieldSuggestion.status` 在服务端和客户端增加可选/默认的 `pending` 解析；旧客户端忽略新增状态字段仍能展示候选，但不会获得跨设备历史 UI。状态端点接受幂等的 `accepted`、`rejected`、`stale` 更新，并拒绝未知状态。

### 4. Diff 片段携带范围而不是 HTML

`DiffSegment` 增加 `beforeStart`、`beforeEnd`、`afterStart`、`afterEnd` 四个可空范围。文本 token 生成时记录 UTF-16 code-unit 范围，方便 Flutter 文本控件定位；正文继续优先按句子/段落切分，短文本使用字符级 token，话题集合差异的范围保持为空。显示层仍使用普通 Flutter 文本样式，不解析服务端 HTML。

### 5. 客户端恢复流程

编辑器打开已保存笔记时，若注入 `loadSuggestions`，先读取该笔记候选历史，并用当前字段值作为本次会话的冲突基线。最新 pending 候选继续显示在字段面板，全部候选在历史面板按时间倒序展示；已解决或 stale 候选只读。采纳/拒绝通过可选回调同步服务端，回调失败时保留本地状态并提示用户，不自动覆盖当前输入。

## Risks / Trade-offs

- [Risk] 候选值 JSONB 会增加笔记历史数据量 → 只保存字段候选和必要审核元数据，不保存 prompt/trace；按 note/status 查询并提供历史列表，后续可增加保留策略。
- [Risk] 客户端范围偏移可能因 Unicode 组合字符与平台文本索引不同而不完全等价 → 统一记录 UTF-16 code-unit 范围，并将其限定为展示定位，不作为持久化 patch 执行。
- [Risk] 接受状态先于草稿保存成功可能产生状态不一致 → 状态同步回调失败时保留 pending/本地候选并提示；服务端不在状态端点修改正式笔记，正式内容仍以保存接口为准。
- [Risk] 旧客户端不理解状态或范围字段 → 新字段提供默认值，服务端响应保留已有 FieldSuggestion 字段，旧客户端仍可读取候选值。

## Migration Plan

1. 添加 Alembic migration 创建 `field_suggestions` 表和索引。
2. 发布服务端 DTO、repository 和候选历史端点；旧的字段重生成请求继续可用，但已保存笔记的候选开始持久化。
3. 更新 Flutter API/model/editor，启用候选加载和状态同步回调。
4. 验证旧草稿、旧客户端形状、跨设备读取、stale 冲突和回滚路径；回滚代码时保留表，避免丢失候选历史。
