# 内容工作流契约

## 资源

| 资源 | 说明 |
| --- | --- |
| `AccountProfile` | 账号定位、月龄范围、表达风格和内容边界 |
| `ContentColumn` | 可启用或停用的内容栏目 |
| `SourceExperience` | 用户提供的真实育儿经历 |
| `NoteDraft` | 标题、正文、话题、封面文案、配图建议和可选 `style_form` |
| `FactLedger` | 从 `SourceExperience` 派生的来源事实、观察、观点和禁止推断边界 |
| `ClaimAudit` | 生成声明的 `supported` / `uncertain` / `unsupported` 状态、证据和风险级别 |
| `ReviewResult` | 提示级或阻断级内容检查结果，以及当前版本的声明审计快照 |
| `Asset` | 账号范围内的图片素材 |
| `PublishRecord` | 用户手动发布后的状态和数据 |
| `StyleForm` | 表达形式：`popular_science`（科普）/ `experience`（经验）/ `advertorial`（软文） |
| `AgentTrace` | 风格转换 agent 的逐步执行记录（阶段标签、工具名、入参与结果摘要） |
| `StyledNoteResponse` | 风格化草稿 + `AgentTrace` 的响应结构 |
| `AgentRun` | 异步 Agent 运行的状态、阶段、诊断、尝试次数和关联笔记引用 |
| `AgentRunEvent` | AgentRun 的有序阶段/模型/工具/终态事件，可通过 SSE 断线续读 |
| `FieldSuggestion` | 针对一个可编辑字段、绑定笔记的可恢复 AI 候选历史、基础摘要、审核结果和来源证据 |
| `EditableField` | `title` / `body` / `hashtags` / `cover_copy` 四个规范化字段名 |

## 状态

- 草稿：`draft`
- 待人工复核：`needs_review`
- 可复制：`ready`
- 已发布：`published`
- 不发布：`discarded`

## 错误分类

- `validation_error`：请求字段不完整或格式错误
- `generation_failed`：模型不可用、超时或输出无法解析
- `blocking_review`：内容包含诊断、用药、虚构事实或其他阻断级风险
- `asset_error`：图片类型、大小或存储操作失败
- `server_error`：不透明的服务端错误，响应使用 request ID 追踪

## 生成语义

生成请求必须携带账号配置、选定栏目、表达形式（`form`）和 `SourceExperience`。真实模型路径由风格转换 agent 直接根据来源经历起草并风格化；本地 `stub` 路径返回中性草稿，供开发和测试使用。agent 的逐步执行过程以 `agent_trace` 随响应返回。服务端不得将用户未提供的关键经历、结果或个人体验作为已发生事实返回。局部重新生成在内存中将候选合并到完整草稿并执行统一审核，但 HTTP 只返回目标字段的 `FieldSuggestion`，不自动替换当前草稿；旧草稿缺少 `style_form` 且请求未显式提供形式时返回 `style_form_required`。

所有生成、整篇风格重写、字段重生成和保存路径都必须重新建立 Fact Ledger 并执行 Claim Audit。`ReviewResult` 必须绑定 `source_digest`、`content_digest`、`audit_version` 和 `policy_version`；审核结果缺失、缺少本版本声明审计或 digest 不匹配时状态只能是 `needs_review`。存在 `blocking` 或 `warning` finding，或存在 `uncertain` / `unsupported` 声明时也不能进入 `ready`。服务端不信任客户端提交的 `status` 或 `review` 来绕过该计算。

无法从来源事实得到证据的声明不得标记为 `supported`。危险睡眠、诊断/用药、产品绝对安全或发育功效、虚构关键经历和伪造外部背书属于 blocking；无法确认的概括、因果关系或一般化结论至少属于 warning，并向用户返回命中文本或来源证据。

## 风格转换端点

- `POST /api/v1/notes/generate`：请求体新增必填 `form`（`StyleForm`），响应为 `StyledNoteResponse`（`draft` + `agent_trace`）。
- `POST /api/v1/notes/style`：对已有草稿按 `form` 重新风格化，请求体 `{draft, form}`，响应为 `StyledNoteResponse`。
- `POST /api/v1/notes/regenerate-field`：请求体为 `{draft, field, form?}`，`field` 只能是 `title`、`body`、`hashtags` 或 `cover_copy`；响应为目标字段 `FieldSuggestion`，而不是完整 `NoteDraft`。`form` 缺失时沿用草稿的 `style_form`，两者都缺失返回 HTTP `409` / `style_form_required`；无效字段由请求校验返回 HTTP `422`。
- `GET /api/v1/notes/{note_id}/suggestions`：读取该笔记的候选历史，按创建时间倒序返回 `pending`、`accepted`、`rejected` 和 `stale` 候选；当前字段或完整内容 digest 变化时，未决候选返回 `stale`。
- `PATCH /api/v1/notes/{note_id}/suggestions/{suggestion_id}`：只更新候选状态，不修改笔记正文；允许显式标记 `accepted`、`rejected` 或 `stale`，重复更新已结束状态保持幂等。

`FieldSuggestion` 至少包含：

- `suggestion_id`、`note_id`、`field` 和候选 `value`；标题与话题的 `value` 保持字符串列表，正文与封面文案保持字符串；
- `base_field_digest` 和 `base_content_digest`，表示请求时目标字段及完整可编辑内容的基础摘要；
- 候选完整草稿计算出的 `review`，以及目标字段相关的 `evidence` / `evidence_fact_ids`；
- `status`（`pending` / `accepted` / `rejected` / `stale`）和 `created_at`。已保存笔记的候选写入服务端历史，但不保存 prompt、模型原始消息、密钥、访问令牌或图片内容。

客户端在发起请求前保存目标字段的本地基础值，并在打开已保存笔记时加载候选历史。候选通过客户端 Diff 展示“当前内容 → AI 建议”，用户必须显式采纳或拒绝；采纳遇到基础值冲突或 `stale` 状态时必须明确处理，不能静默覆盖。候选状态更新不直接修改笔记，保存时仍发送完整草稿并重新执行 Fact Ledger、Claim Audit、`NoteStatus` 和导出门禁。

客户端还可以展示可靠 AI 初稿与当前编辑之间的 Diff：正文按段落/句子优先并提供 before/after 文本范围，短文本按字符片段，话题按集合且不伪造字符范围。服务端不返回 HTML 或平台特定 Diff 标记；来源关系使用审核证据和字段级 `matched_text` 展示。

`NoteDraft`、草稿保存请求、生成响应和字段重生成请求中的 `style_form` 均可为空，以兼容旧草稿。新生成和显式风格重写必须保存该值。

`AgentTrace` 每步包含 `order`、`kind`（`model` / `tool` / `phase`）、`label` 与 `summary`，并可选包含 `phase`（`collect_context` / `draft` / `critique` / `revise` / `safety_review` / `finalize`）；trace 只用于展示与调试，不落库、不包含密钥或完整原始消息。旧客户端忽略新增的可选 `phase` 字段仍可正常展示。

Agent Runtime 在服务端维护独立的总步骤、修订、工具调用、重复错误和阶段耗时预算。预算或重复错误触发时返回稳定失败代码，例如 `agent_max_steps`、`agent_revision_budget_exhausted`、`agent_tool_budget_exhausted`、`agent_repeated_error` 和 `agent_stage_timeout`；失败运行保留截断后的 trace，不把未通过结果标记为可用。

长耗时运行可以使用异步 AgentRun 生命周期：创建后返回 `run_id` 和关联 `note_id`，状态依次可能为 `queued`、`running`、`completed`、`failed`、`cancelled` 或 `interrupted`。客户端通过 `GET /api/v1/agent-runs/{run_id}` 查询状态，通过 `GET /api/v1/agent-runs/{run_id}/events` 读取 SSE 事件，并可调用 `/cancel` 或 `/resume`。事件 ID 从 1 开始递增；请求参数 `after` 或 `Last-Event-ID` 用于断线续读。

客户端记录最后处理的事件序号；SSE 连接断开后使用 `after=<last_sequence>` 重连并按序号去重。生成页面保留失败或中断的 `run_id` 与本地 `SourceExperience`，允许“继续运行”或“重新生成”；只有服务端明确返回 `completed` 且读取到最终笔记时才进入编辑器，取消、失败和中断运行不得作为成功结果打开。

AgentRun 只保存关联笔记和运行诊断，不保存完整 prompt、模型消息、工具原始参数、模型密钥、访问令牌、用户正文或图片内容。服务端重启后遗留的 `running` 运行标记为 `interrupted`；恢复是基于已持久化笔记输入的重新执行，不承诺模型上下文 checkpoint。

评测 runner schema version 4 在每条 run record 的 `agent_diagnostics` 中保存运行状态、最终阶段、计数器、失败代码、模型调用次数和 prompt/completion/total token；顶层 `evaluation_context` 只保存案例集、scorecard、prompt、style profile、Agent 配置和门禁 manifest 的版本/摘要，以及显式价格配置和估算成本。历史 schema version 1/2/3 记录保持兼容读取，但缺少版本、usage 或成本证据的旧记录不能通过 P1-06 quality gate。评测记录不保存完整 prompt、模型消息、密钥、访问令牌、图片内容或未脱敏用户正文；该诊断结构暂不进入数据库，也不改变 `NoteStatus` 或导出门禁语义。

## V1 endpoints

- `PUT /api/v1/accounts/{account_id}`：保存账号配置
- `GET /api/v1/accounts/{account_id}`：读取账号配置
- `POST /api/v1/accounts/{account_id}/columns`：创建内容栏目
- `GET /api/v1/accounts/{account_id}/columns`：读取内容栏目
- `POST /api/v1/notes/generate`：生成结构化笔记草稿
- `POST /api/v1/notes/style`：按表达形式重新风格化已有草稿
- `POST /api/v1/notes/regenerate-field`：局部重新生成
- `GET /api/v1/notes/{note_id}/suggestions`：读取字段候选历史
- `PATCH /api/v1/notes/{note_id}/suggestions/{suggestion_id}`：更新候选状态
- `POST /api/v1/agent-runs`：创建异步 Agent 运行
- `GET /api/v1/agent-runs/{run_id}`：读取 AgentRun 状态和诊断
- `GET /api/v1/agent-runs/{run_id}/events`：读取带游标的 SSE 运行事件
- `POST /api/v1/agent-runs/{run_id}/cancel`：请求取消运行
- `POST /api/v1/agent-runs/{run_id}/resume`：恢复失败、取消或中断运行
- `POST /api/v1/accounts/{account_id}/notes`：生成并保存笔记草稿
- `GET /api/v1/accounts/{account_id}/notes`：列出账号草稿（按更新时间倒序）
- `GET /api/v1/notes/{note_id}`：读取笔记草稿
- `PUT /api/v1/notes/{note_id}`：保存草稿编辑并新增一个草稿版本
- `GET /api/v1/notes/{note_id}/versions`：读取草稿版本历史（旧到新）
- `POST /api/v1/notes/{note_id}/publish-record`：保存手动发布记录和数据
- `POST /api/v1/accounts/{account_id}/assets`：上传账号范围内的图片素材
- `GET /api/v1/accounts/{account_id}/assets`：列出账号素材
- `PUT /api/v1/accounts/{account_id}/assets/order`：保存素材顺序
- `GET /api/v1/assets/{asset_id}`：下载素材
- `DELETE /api/v1/assets/{asset_id}`：删除素材

## 发布边界

客户端可以复制标题、正文和话题、下载素材并记录发布结果。导出请求在审核结果缺失、当前版本审核过期或存在 blocking 风险时拒绝，并返回可展示的风险原因；warning/uncertain 草稿保留 `needs_review` 和提示。API 不提供小红书登录、自动发布、点赞或评论操作。
