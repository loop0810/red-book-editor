# 内容工作流契约

本文档是 Flutter 客户端和 Python 服务端共同依赖的当前契约。它只描述跨端可依赖的产品行为、请求、响应、状态和错误语义；Agent 内部 trace、Fact Ledger、Claim Audit 和模型诊断不是普通客户端的信息架构。

## 核心资源

| 资源 | 说明 |
| --- | --- |
| `AccountProfile` | 账号领域、定位、范围、语气、边界和常用表达 |
| `DomainStrategyPack` | 领域版本、补充输入、质量规则、安全政策和可用工具 |
| `ContentColumn` | 账号范围内的内容栏目和上下文 |
| `ContentBrief` | 本次内容的主题/重心、原始素材、领域上下文和可选图片 |
| `NoteDraft` | 标题、正文、话题、封面文案、配图建议和草稿状态 |
| `UserFacingIssue` | 需要用户处理时的简短、准确、可行动提示 |
| `Asset` | 账号范围内的图片素材 |
| `DraftVersion` | 可恢复的草稿版本 |
| `PublishRecord` | 用户主动记录的手动发布状态和表现数据 |
| `StyleForm` | 表达形式，例如 `popular_science`、`experience`、`advertorial` |

以下资源属于服务端内部质量和运行能力，普通 C 端不直接展示：

| 内部资源 | 用途 |
| --- | --- |
| `FactLedger` | 保存来源事实、观察、观点、未知和禁止推断边界 |
| `ClaimAudit` | 审计生成声明的来源支持和风险 |
| `ReviewResult` | 领域策略执行后的内部审核快照 |
| `AgentTrace` | Agent 阶段、工具和模型摘要，用于评测、运维和授权调试 |
| `AgentRun` | 长耗时运行状态、预算、失败码和内部事件 |

## 内容输入

新的生成语义以 `ContentBrief` 为核心：

```json
{
  "focus": "宝宝周岁宴",
  "raw_material": "想简单办，不准备大型酒宴，更在意家人一起吃顿饭",
  "domain_context": {
    "baby_month": 12
  },
  "asset_ids": []
}
```

约束：

- `focus` 是用户明确的内容主题/重心，必填；标题和选题角度必须优先围绕它。
- `raw_material` 是用户原始素材和事实来源，必填；服务端不得把未提供的经历、结果或个人体验写成已发生事实。
- `domain_context` 由领域策略包定义，可为空；育儿月龄等字段不属于所有领域的通用必填项。
- 旧客户端的 `SourceExperience` 可以在兼容层转换为 `ContentBrief`，但新客户端不应继续扩散育儿专属字段。
- `account_id`、`column_id`、`domain_id` 和 `style_form` 必须来自当前账号和服务端返回的有效配置，客户端不得硬编码随机栏目 ID。

## 内容输出

普通客户端的用户结果投影至少包含：

```json
{
  "draft": {
    "title_candidates": ["..."],
    "body": "...",
    "hashtags": ["#..."],
    "cover_copy": "...",
    "image_suggestions": ["..."]
  },
  "issues": []
}
```

响应必须满足：

- 至少一个标题候选明确体现 `focus`；
- 正文、话题和配图建议符合账号领域、定位和所选表达形式；
- 配图建议是内容产物，不要求接入图片生成服务；
- 用户可以编辑、复制、保存和请求单字段重新生成；
- 生成失败只返回稳定错误和可执行的重试/继续语义，不返回模型原始消息。

`agent_trace`、完整 `review`、`claim_audit`、来源证据、命中文本和运行诊断可以保存在服务端或内部调试响应中，但不得成为普通 C 端结果模型的默认展示字段。

## 领域策略

每个账号引用一个有效的领域策略包：

```text
domain_id + version
  ├─ supplemental_input_schema
  ├─ generation_context
  ├─ quality_rules
  ├─ safety_policy
  ├─ allowed_tools
  └─ user_facing_issue_projection
```

通用 Content Agent 负责“理解主题 → 组织角度 → 生成 → 检查 → 修订”。领域策略包负责领域差异。策略包不可用时必须报配置错误，不能静默使用其他领域。

## 状态

- `draft`：已创建或仍可编辑的草稿；
- `ready`：服务端内部检查完成且没有当前领域的 blocking 风险，可以继续复制/导出；
- `needs_review`：存在需要服务端或用户处理的真实阻断、上下文缺失或内部审核未完成；用户只看到必要的 `issues`；
- `published`：用户主动记录已发布；
- `discarded`：用户主动标记不再使用。

普通 warning 或低置信度自然改写不能自动生成疾病/用药提示，也不能仅凭脆弱的逐字匹配阻止普通内容编辑和复制；是否影响 `ready` 由领域策略明确决定。

## 用户问题投影

正常内容的 `issues` 必须为空，不显示固定免责声明或内部审核信息。

真实阻断问题的 `issues` 必须包含：

- 与实际风险匹配的稳定类别；
- 简短、非技术化的说明；
- 可选的目标字段；
- 用户下一步可以执行的修改方向。

例如，非医疗的周岁宴内容不得显示“请检查疾病判断、用药”。如果用户确实请求药物剂量，则可以显示与用药请求对应的提示并阻止复制/导出。

## 主要端点

- `POST /api/v1/accounts`：在当前无登录的本地工作台创建账号配置，由服务端生成账号标识；
- `PUT /api/v1/accounts/{account_id}`：保存账号领域和配置；
- `GET /api/v1/accounts/{account_id}`：读取账号配置；
- `POST /api/v1/accounts/{account_id}/columns`：创建内容栏目；
- `GET /api/v1/accounts/{account_id}/columns`：读取启用栏目；
- `POST /api/v1/notes/generate`：根据账号、栏目、领域、ContentBrief 和表达形式生成用户结果；
- `POST /api/v1/notes/style`：按表达形式重新生成已有草稿；
- `POST /api/v1/notes/regenerate-field`：只返回目标字段候选；
- `GET /api/v1/notes/{note_id}`：读取草稿；
- `PUT /api/v1/notes/{note_id}`：保存草稿并创建版本；
- `GET /api/v1/notes/{note_id}/versions`：读取次级版本历史；
- `POST /api/v1/accounts/{account_id}/assets`：上传账号范围内的图片素材；
- `GET /api/v1/accounts/{account_id}/assets`：列出账号素材；
- `POST /api/v1/notes/{note_id}/publish-record`：用户主动记录手动发布结果。

AgentRun 的创建、状态、事件、取消和恢复端点仍可供客户端完成可靠的长耗时流程，但普通用户页面只表现为加载、成功、失败、继续或重试，不展示阶段列表。

当前版本的账号是内容生成上下文，不是产品用户身份。首次使用可以直接创建账号和默认栏目；注册、登录、密码、会话和多用户权限属于后续独立身份能力，不得由客户端伪造一个登录流程来替代。

## 内部审核和安全边界

所有生成、重写、字段候选和保存路径都必须在服务端执行当前领域策略所需的事实和安全检查。服务端可以保存 `source_digest`、`content_digest`、`audit_version` 和 `policy_version`，用于防止审核过期或客户端伪造状态。

内部 Claim Audit 必须允许自然语言改写、助词、顺序和标点变化；不能把每个无法逐字匹配的句子都变成用户错误。来源外关键经历、诊断、用药方案、危险建议、确定性安全保证和领域策略定义的其他 blocking 结果仍不得静默放行。

客户端不持有模型密钥，不直接调用模型供应商，不决定审核结果，也不渲染完整内部审计结构。

## 手动发布边界

客户端可以复制标题、正文和话题，使用配图建议、下载用户素材并记录发布结果。API 不提供小红书登录、自动发布、点赞、评论或抓取操作。
