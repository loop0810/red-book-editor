## 1. 模型网关与 DeepSeek 适配器

- [x] 1.1 在 `domain/ports.py` 增加 `ModelGateway` 协议与 `ModelResponse`（text / tool_calls 联合）类型
- [x] 1.2 实现 `infrastructure/llm/deepseek.py`：DeepSeek 适配器（OpenAI 兼容消息与工具调用协议、超时、重试、结构化解析）
- [x] 1.3 服务端配置与 `.env.example` 增加 `DEEPSEEK_API_KEY`、`DEEPSEEK_MODEL`、`DEEPSEEK_BASE_URL`，并校验必填 key
- [x] 1.4 保留 `MODEL_PROVIDER=stub` 回退路径，按配置选择适配器；开发与测试不依赖真实 key
- [x] 1.5 单元测试：工具调用往返、纯文本回退、解析失败重试、日志不包含密钥
- [x] 1.6 成功模型响应增加进程内 TTL/LRU 缓存，重复请求复用已解析结果

## 2. Agent 运行时

- [x] 2.1 在 `domain/agent.py` 实现 `Tool` 协议、`AgentTraceStep`、`AgentRuntime` 循环（最大步数、结构化输出校验、错误语义）
- [x] 2.2 运行时记录逐步 trace（阶段标签、工具名、入参/结果摘要，截断且不落库）
- [x] 2.3 单元测试：工具调用回填、超过最大步数报错并保留部分 trace、最终输出非法时重试、trace 顺序正确

## 3. 风格档案

- [x] 3.1 在领域契约增加 `StyleForm` 枚举（popular_science / experience / advertorial）与风格档案 Pydantic schema
- [x] 3.2 创建三份 YAML 档案（`server/src/red_book_editor_server/style_profiles/`）：钩子、结构模板、语气、富文本规则、三层标签池、封面模式、CTA
- [x] 3.3 实现档案加载器与 schema 校验；测试：未知 form 报错、schema 违规报错、启动时全量校验通过
- [x] 3.4 按观察到的育儿笔记模式填充标签池（泛标签 / 精准标签 / 蹭热点标签三层）

## 4. 风格转换 agent

- [x] 4.1 实现工具：`load_style_profile`、`suggest_tags`、`critique_draft`（含确定性事实保持核对）、`finalize_note`
- [x] 4.2 组装风格转换工作流（读档案 → 规划结构 → 写作 → 自评 → 修订 ≤2 轮 → 输出）于 `modules/content_workflow/styling/`
- [x] 4.3 实现富文本装饰器（emoji/分隔符号规则、标签数量裁剪、CTA、封面文案模式）
- [x] 4.4 假网关注入的黄金路径测试：成功风格化、事实保持违规触发修订、修订达到上限、trace 完整

## 5. 契约与 API

- [x] 5.1 在 `domain/contracts.py` 增加 `AgentTraceStep`、`StyledNoteResponse` DTO
- [x] 5.2 更新 `docs/contracts/CONTENT_WORKFLOW_CONTRACT.md`：`form` 字段、`/notes/style` 端点、trace 与错误语义
- [x] 5.3 `POST /api/v1/notes/generate` 增加必填 `form`，响应附 `agent_trace`；新增 `POST /api/v1/notes/style`
- [x] 5.4 风格化路径不调用 `review_draft`，草稿直接可编辑/可复制；局部重生成沿用原 form
- [x] 5.5 契约测试：成功响应、未知 form 返回 422、模型失败保留输入、局部重生成不覆盖未选字段

## 6. 客户端

- [x] 6.1 `app_core` 增加 `StyleForm`、`AgentTraceStep`、`StyledNoteResponse` 模型与 API 客户端方法
- [x] 6.2 `note_creation` 生成前增加表达形式选择（科普 / 经验 / 软文三个预设）
- [x] 6.3 `note_creation` 展示风格化草稿与可折叠 agent trace（读档案/规划/写作/自评/修订/完成）
- [x] 6.4 局部重生成保留表达形式；`account_workspace` 栏目预设更新为三种表达形式
- [x] 6.5 客户端测试：模型解析、表达形式选择与 trace 展示的 widget 测试

## 7. 验证

- [x] 7.1 服务端：`make lock-check`、`make format-check`、`make typecheck`、`make test`、`make integration-test`
- [x] 7.2 客户端：`dart format --output=none --set-exit-if-changed .`、`flutter analyze`、`flutter test`
- [x] 7.3 用真实 DeepSeek key 做一次端到端人工验证：生成风格化草稿并核对 trace 与事实保持
