## Context

当前 `NoteEditorPage` 只有一个可编辑草稿快照；字段重生成虽然在服务端内部只生成目标字段，但响应仍是完整 `NoteDraft`，客户端收到后会直接覆盖控制器内容。已有 `DraftVersion`、`ReviewResult`、`ClaimAuditItem.field` 和 AgentRun SSE，可以作为本 change 的基础。详见 proposal.md - Why。

实现继续遵守：领域逻辑不依赖 FastAPI、SQLAlchemy 或具体模型 SDK；服务端不保存模型原始消息、完整 prompt、用户正文副本、图片内容、密钥或令牌；保存、采纳和导出都不能绕过 Fact Ledger、Claim Audit、NoteStatus 和 export gate。

## Goals / Non-Goals

**Goals:**

- 将字段重生成变成目标字段候选建议，并让客户端显式管理当前值、AI 初稿和待处理候选。
- 在不新增数据库表的前提下，保护会话内的用户编辑，支持字段级 Diff、采纳、拒绝和冲突提示。
- 让候选建议和当前草稿都使用统一审核语义，并把来源证据、审核发现关联到字段。
- 补齐 AgentRun 失败后的手动重试/继续运行和 SSE 事件序号续读。

**Non-Goals:**

- 不持久化 pending suggestion，不做跨设备或关闭页面后的建议恢复。
- 不做 token 流、不引入 WebSocket、不实现模型上下文 checkpoint。
- 不做字符级安全高亮；本轮只保证字段和命中文本定位。
- 不扩展到图片理解、Memory、RAG、MCP 或自动发布。

## Decisions

### 1. 用三层编辑状态区分 AI 初稿、当前草稿和候选建议

客户端编辑会话维护：

```text
aiBaseline[field]       初次生成或可恢复的 AI 字段快照
currentDraft[field]     用户当前正在编辑的字段
pending[field]          尚未采纳的 AI 候选列表
```

`NoteDraft` 仍是保存和审核的规范对象；上述状态只属于编辑器会话。新生成页面直接从 `StyledNoteResponse.draft` 捕获 `aiBaseline`。重新打开草稿时优先使用最早可用的草稿版本作为基线；没有可靠基线时不显示“用户编辑 Diff”，但仍可显示“候选建议 Diff”。

选择三层状态而不是继续修改 `NoteDraft` 的原因是：用户输入框中的未保存内容不能被服务端返回的候选覆盖，且一个字段可以同时存在多个尚未采纳候选。

### 2. 字段重生成响应改为目标字段建议 DTO

现有字段重生成端点改为返回 `FieldSuggestionDto`，而不是完整 `NoteDraft`。响应包含：

- `suggestion_id`、`note_id`、规范化的字段名；
- 该字段的候选值；标题和话题字段保留列表结构；
- 请求时的 `base_field_digest` 和 `base_content_digest`；
- 基于完整候选草稿计算的 `ReviewResult` 或字段审核投影；
- 目标字段相关的来源证据和创建时间摘要。

服务端仍然用完整草稿在内存中合并候选并执行统一审核，但 HTTP 响应只暴露目标字段和审核/证据元数据。客户端在发请求前保存目标字段的本地快照，用于渲染 Diff 和检查冲突。由于这是仓库内已知客户端的 **BREAKING** 契约变更，Flutter `app_core`、页面回调和所有 API 测试在同一 change 中迁移。

### 3. 采纳先改变会话草稿，保存时由服务端最终审核

点击“采纳”只把候选值合并到本地 `currentDraft` 的目标字段，并移除该 pending suggestion；其他字段和来源对象保持不变。编辑器显示候选审核结果，用户点击保存时仍调用现有保存端点，由服务端重新审核完整草稿并创建版本。

采纳前比较当前字段 digest 与 suggestion 的 `base_field_digest`：

```text
current digest == base digest  → 允许直接采纳
current digest != base digest  → 标记冲突，用户必须明确选择
```

冲突选择“使用候选”也只替换目标字段，不会静默覆盖；选择“保留当前”则拒绝该候选。未保存的本地采纳内容不具备导出资格，导出仍以服务端最新审核快照为准。

### 4. Diff 在客户端渲染，服务端只提供稳定输入

服务端不返回 HTML、富文本标记或平台特定的 Diff 格式。客户端根据 `baseValue`、`currentValue` 和 `candidateValue` 计算展示结果：

- 正文按段落/句子优先比较，减少中文逐字符 Diff 的噪声；
- 标题和封面文案使用短文本片段比较；
- 话题使用新增、删除和保留集合比较；
- Diff 只用于展示，不参与安全判断或状态计算。

来源关系使用审核证据面板展示，不使用绿色/红色 Diff 颜色替代“有来源/不确定/未找到来源”。

### 5. 审核发现按字段生成，暂不承诺字符偏移

审核器按字段处理文本，`ReviewFindingDto` 增加可选字段标识；新生成的 finding 必须带规范化字段名和 `matched_text`。旧草稿或旧审核结果缺少字段时保持兼容读取，并在下一次生成/保存时重新生成。

客户端把字段名映射到对应编辑控件，点击审核问题可以滚动或聚焦目标字段。字符范围需要处理富文本、中文索引和多次命中，留待后续 change，不在本轮伪造精确位置。

### 6. 复用现有 AgentRun SSE 游标完成恢复体验

客户端记录最后收到的事件序号，SSE 断开后使用 `after=<last_sequence>` 重新连接，并去重已经处理的事件。生成页保留失败/中断的 `run_id`，对可恢复状态提供“继续运行”，对其他失败提供“重新生成”。服务端仍以 AgentRun 生命周期和数据库状态为权威，不把客户端显示的进度当作成功结果。

### 7. 延后建议持久化

候选建议只保存在编辑器会话状态，不新增 `suggestions` 表或 migration。相比立即持久化，这能保留未保存本地编辑的自然交互，并把本轮风险限制在页面关闭后丢失候选；未来若要跨设备恢复，可在不改变字段建议 DTO 的前提下增加服务端 suggestion repository 和生命周期。

## Risks / Trade-offs

- [Risk] 重新打开草稿时无法可靠识别最初 AI 内容 → 优先读取最早版本作为基线；缺少基线时隐藏编辑 Diff，不阻塞普通编辑和建议 Diff。
- [Risk] 会话关闭会丢失未采纳建议 → 在页面关闭或返回时提示仍有 pending suggestion；后续再评估持久化。
- [Risk] 目标字段响应变更会影响旧客户端 → 明确标记 BREAKING，仓库内同步迁移 Client、测试和契约文档。
- [Risk] 中文文本 Diff 可能产生噪声 → 采用字段专属的段落、短文本和集合比较，并把 Diff 限定为辅助阅读。
- [Risk] 用户采纳包含风险的候选 → 候选预览和保存都保留审核结果，export gate 继续阻止过期、缺失或 blocking 审核。
- [Risk] SSE 重连造成重复事件或事件乱序 → 以事件序号作为唯一游标，客户端去重，终态事件之后停止重连。

## Migration Plan

1. 增加领域和跨端 `FieldSuggestion` 契约、字段 digest、候选审核投影和兼容解析。
2. 修改服务端字段重生成流程：内部完整合并和审核，HTTP 只返回目标字段建议；审核器补充字段关联。
3. 修改 `app_core` API Client、回调和测试，完成 breaking response 迁移。
4. 在 `NoteEditorPage` 增加会话状态、字段 Diff、候选列表、采纳/拒绝和冲突处理。
5. 在新建页面接入失败重试、继续运行、SSE 游标重连，并保留现有取消语义。
6. 更新内容工作流契约、OpenSpec 主 spec 和集成回归测试；执行服务端与 Flutter 验证。

若需要回滚，客户端可以暂时隐藏建议交互并停止调用新字段响应；不需要数据库 downgrade，因为本 change 不新增 schema。
