## Context

当前服务端 `MODEL_PROVIDER=stub`，`StubContentGenerator` 输出写死模板，无真实模型、无 prompt、无风格知识；`ContentGenerator.generate` 接口只接收 `source + account_id + column_id`，账号的风格档案（`tone` / `positioning` / `common_expressions`）与栏目说明到不了生成器。安全审查为确定性正则，会阻断"剂量""专家建议"等育儿领域常见写法。动机与范围见 proposal.md，行为契约见各 specs。

## Goals / Non-Goals

**Goals:**

- 手写一个最小 agent 运行时（不引入框架），让"模型决策 → 工具执行 → 结果回填"的循环机制在本项目中可见、可测试、可扩展。
- 以 DeepSeek（`deepseek-chat`）作为第一个真实模型适配器，走可插拔模型网关端口。
- 建立三份表达形式风格档案（科普 / 经验 / 软文），以 YAML 存于服务端代码库并随版本管理。
- 实现育儿风格转换 agent：读取档案 → 规划结构 → 写作 → 自评 → 修订 → 输出结构化草稿，全程记录 trace。
- 风格化结果与 trace 通过 API 返回，客户端展示表达形式选择与 agent 步骤。
- V1 风格化路径不调用阻断级内容检查（范围声明，见 specs）。

**Non-Goals:**

- 不引入 LangGraph 等 agent 框架——学习目标优先，先理解底层机制，后续再评估框架。
- 不做多领域（仅育儿），不做发布数据回流、记忆与账号长期画像。
- 风格档案不进数据库、不做客户端在线编辑；不新增数据库 schema。
- 不做自动发布、不做小红书数据抓取；客户端不持有模型 key。

## Decisions

### 1. 手写最小 agent 运行时，放在领域层

新增 `domain/agent.py`：`AgentRuntime` 持有一个模型网关和工具注册表，按循环执行：

```text
messages = [system, user]
for step in 1..max_steps:
    response = gateway.chat(messages, tools=tool_schemas)
    记录 trace(模型消息摘要)
    if response.tool_calls:
        执行每个工具，结果以 tool 消息回填 messages，继续
    else:
        校验 response.content 是否符合最终结构化 schema
        通过 → 返回 (结构化结果, trace)
        不通过 → 把校验错误回填给模型，重试（≤2 次）
超过 max_steps → 返回包含部分 trace 的 AgentError
```

工具协议为 `Tool`（名称、描述、入参 schema、异步执行函数）；运行时只负责调度与记录，不感知业务。`AgentTraceStep` 记录步骤序号、阶段标签、工具名、入参/结果摘要（截断，不落库、不记录密钥与完整消息）。

替代方案：直接用 LangGraph 编排。更快，但掩盖循环、工具调用与状态管理机制，与"学 agent"目标冲突，不采用。

### 2. 模型网关端口 + DeepSeek 适配器

`domain/ports.py` 增加 `ModelGateway` 协议：`chat(messages, *, tools=None) -> ModelResponse`，其中 `ModelResponse` 为 `text | tool_calls` 的联合类型。`infrastructure/llm/deepseek.py` 实现 DeepSeek 适配器（OpenAI 兼容接口）：

- 配置：`DEEPSEEK_API_KEY`（必填）、`DEEPSEEK_MODEL`（默认 `deepseek-chat`）、`DEEPSEEK_BASE_URL`、超时与重试次数；key 只从环境变量读取，请求/响应日志做脱敏。
- 工具调用与 JSON 输出统一走模型消息协议，返回原始结构，由调用方解析。
- 解析失败、超时由上层 `generate_with_retry` 风格的重试逻辑兜底，错误语义与现有 `generation_failed` 一致。
- 对成功的模型响应按模型、消息和工具定义做进程内 TTL/LRU 缓存；网关实例跨请求复用，重复请求复用已解析的 `ModelResponse`，不把 key 写入缓存键，也不落盘。缓存仅用于减少相同请求的重复调用，不替代 agent 的顺序工具循环。

`StubContentGenerator` 保留用于本地开发与测试（`MODEL_PROVIDER=stub`），适配器按配置切换，测试用假网关注入。

### 3. 风格档案：YAML + schema 校验

档案放在 `server/src/red_book_editor_server/style_profiles/<form>.yaml`，形式枚举 `StyleForm = popular_science | experience | advertorial`。每个档案：

```yaml
form: popular_science
display_name: 科普
hooks:            # 标题钩子模式
  - "权威背书 + 结果"
  - "数字 + 反差"
structures:       # 正文结构模板（agent 从中选择）
  - name: 科普结构
    sequence: [钩子, 分级清单, 实操要点, 红线/误区, CTA]
tone:
  person: 第一人称妈妈视角
  words: [亲测, 直接抄作业, 新手爸妈]
  forbidden: []
rich_text:
  emoji_rules: "每段不超过 2 个 emoji/符号"
  separators: ["•", "|"]
  tag_count_range: [6, 15]
tags:
  generic: [育儿干货, 亲子育儿]
  precise: [宝宝护理, 新手宝妈经验]
  trending: [崔玉涛育儿, 宝宝发烧]
cover:
  pattern: "大字短句：数字+事件 或 权威背书+结果"
  examples: ["13个月宝宝发烧 40.3度", "崔玉涛说的没错"]
cta: ["新手爸妈直接抄作业", "收藏这份攻略"]
```

加载器对 schema 做 Pydantic 校验（启动与测试时验证），未知 form 返回校验错误。未来多领域 = 新增 `domain/<form>.yaml` + 注册，不改变运行时。

### 4. 风格转换 agent：固定骨架 + agent 细节

工作流步骤由代码固定（保证可预测），步骤内的选择由模型决定（保留 agent 性）：

```text
① load_style_profile(form)        → 工具读档案
② 规划：从 structures 选结构、定钩子   → 模型输出 JSON plan
③ 写作：标题候选/正文/话题/封面/配图    → 模型输出结构化草稿
④ critique_draft(draft, source)    → 工具：钩子/结构/语气/事实保持/富文本评分
⑤ 未达标且未超修订上限 → 带着评分回填模型修订，回到 ③
⑥ finalize_note(...)               → Pydantic 校验后输出 NoteDraft
```

修订上限 2 轮，max_steps 上限 10。`critique_draft` 内含确定性事实核对：从 `SourceExperience` 提取数字、动作与关键名词，检查是否出现在草稿中；缺失或模型自述添加了未提供事实 → 扣分并回填修订指令。这满足"事实保持"要求而不依赖第二套模型。

### 5. 富文本：规则为主、模型辅助

三层标签由规则生成（档案标签池 + 主题关键词去重、按 `tag_count_range` 裁剪），emoji/分隔符号与 CTA 由模型在档案规则约束内选择。封面文案由模型按 `cover.pattern` 生成。装饰逻辑集中在 `modules/content_workflow/styling/decorator.py`，可独立单测。

### 6. API 与契约

- `POST /api/v1/notes/generate` 增加必填 `form: StyleForm`：执行基础生成 + 风格转换，响应 `NoteDraft` 附 `agent_trace`。
- 新增 `POST /api/v1/notes/style`：对已有草稿按 form 重新风格化（复用同一 agent），局部重生成字段沿用原 form。
- 响应模型：`StyledNoteResponse { draft: NoteDraft, agent_trace: [AgentTraceStep] }`。
- 错误语义沿用 `generation_failed` / `validation_error`；未知 form 返回 422。
- 契约文档 `docs/contracts/CONTENT_WORKFLOW_CONTRACT.md` 同步新增。

### 7. 栏目映射与账号范围

不做数据库变更：客户端将栏目预设（科普 / 经验 / 软文）映射为请求中的 `form` 字段，服务端以 `form` 为权威值，栏目说明作为 agent 上下文。账号定位覆盖备孕-孕检-育儿由定位文案承担，不动 `age_range_months` schema。

### 8. 安全边界

风格化路径（`generate` 带 form、`style` 端点）不调用 `review_draft`，草稿直接标记可编辑/可复制；既有检查代码保留，供后续版本接入分级规则。该决策已写入 `content-safety-review` delta spec。

### 9. 客户端

- `app_core`：新增 `StyleForm`、`AgentTraceStep`、`StyledNoteResponse` 模型与 API 方法。
- `note_creation`：生成前选择表达形式（三个栏目预设）；生成后展示风格化草稿 + 可折叠 agent trace（读档案/规划/写作/自评/修订/完成）；局部重生成保留 form。
- `account_workspace`：栏目预设改为科普 / 经验 / 软文。

## Risks / Trade-offs

- [Risk] agent 自由度导致输出不稳定 → 固定骨架 + 每步结构化输出校验 + 自评修订循环。
- [Risk] 真实模型延迟与成本 → max_steps=10、修订≤2 轮、trace 摘要截断；网关超时可配。
- [Risk] 改写编造事实 → `critique_draft` 确定性事实核对 + 提示词强约束 + 规格场景测试。
- [Risk] DeepSeek 工具调用/JSON 模式不稳定 → 网关层容错：解析失败回填重试、支持纯文本回退解析。
- [Risk] 育儿风格与既有阻断规则冲突 → V1 风格化路径不调用阻断检查（范围声明），检查能力保留。
- [Risk] 密钥或正文泄露 → key 只进环境变量；服务端日志不记录正文与完整消息；trace 仅响应内存中返回，不落库。

## Migration Plan

服务端：`.env.example` 增加 `DEEPSEEK_API_KEY`、`DEEPSEEK_MODEL`、`DEEPSEEK_BASE_URL`；无数据库迁移。回滚：`MODEL_PROVIDER=stub` 恢复旧行为，风格端点返回配置错误。客户端：新字段可选，旧版本请求不带 form 时仍走原生成路径（兼容降级）。

## Open Questions

- DeepSeek 具体模型名与工具调用兼容性细节（`deepseek-chat` 系列）在接入时确认，不改规格与任务拆分。
- 软文档案的广告合规边界（明示广告、极限词）V1 不处理，后续单独定义。
