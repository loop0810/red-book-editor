## Context

当前 `AgentRuntime` 只有 `max_steps` 和最终输出重试次数；内容 Agent 通过 system prompt 约束工具顺序，但运行时本身不知道修订、批评和最终整理的阶段，也不会区分工具调用过多与同一校验错误反复出现。Milestone 1 的 Fact Ledger、Claim Audit 和统一安全审核已经是运行后的业务边界，本 change 只增加运行时控制和诊断，不改变安全规则。

## Goals / Non-Goals

**Goals:**

- 将当前自由循环变成由服务端计数和阶段标记约束的运行流程。
- 独立限制修订、工具调用、重复错误、总步骤和阶段耗时。
- 保留现有同步调用方式和客户端可消费的 trace，同时增加稳定的运行诊断字段。
- 让评测 runner 能记录预算耗尽和运行失败，而不是只看到一个通用生成失败。

**Non-Goals:**

- 不在本阶段引入 AgentRun 数据库表、取消/恢复或断点续跑。
- 不引入 SSE、WebSocket、新模型供应商或新的工具类型。
- 不把 Agent Runtime 的成功直接映射为 `NoteStatus.ready`；完整审核仍由内容工作流执行。

## Decisions

### 1. 在现有通用 Runtime 增加运行上下文，而不是重写成编排框架

增加一个内存运行上下文，集中保存当前阶段、计数器、最近错误和开始时间；保留现有 `ModelGateway`、白名单工具和最终 validator。这样可以先解决重复循环问题，不引入 LangGraph 等额外依赖，也不影响现有 stub 测试。

替代方案是把每个阶段拆成独立 Agent 或引入第三方编排框架；这会扩大状态持久化、错误恢复和部署复杂度，不适合当前第一步。

### 2. 用显式预算配置替代从总步数推断修订次数

Runtime 接受 `max_revisions`、`max_tool_calls`、`max_same_error`、`max_steps` 和阶段超时配置，并对配置做最小值校验。默认值保持当前调用路径可用，但将修订和工具消耗分别计数；达到任一预算时使用稳定错误代码终止。

### 3. 由工具元数据和 validator 结果推进阶段

工具注册项增加可选的阶段标签，内容 Agent 为 `load_style_profile`、`critique_draft`、`finalize_note` 提供明确阶段映射；最终 validator 失败进入 `revise`，通过后进入 `finalize`。统一内容安全审核仍在 application service 的现有入口执行，并追加 `safety_review` 阶段 trace，不把安全判断交给模型。

### 4. 错误去重使用稳定摘要，不保存敏感正文

对 validator 错误和工具错误做空白折叠、长度限制和稳定摘要，再用摘要计数连续重复错误。trace 只保存阶段、工具名、计数和截断原因，不保存完整 prompt、模型消息、用户笔记正文或图片内容。

### 5. 保持 API 兼容，新增字段可选

现有 `AgentTraceStep` 的 `kind`、`label` 和 `summary` 保留；运行结果新增的状态、阶段和计数字段使用可选/默认值，旧客户端继续按现有 trace 展示。评测 JSON 新字段也使用兼容读取，历史 runs 不回填、不覆盖。

## Risks / Trade-offs

- [Risk] 严格的重复错误判断可能提前终止本来可以通过的运行 → 只对规范化后完全相同的错误计数，并保留可调阈值。
- [Risk] 阶段标签与模型实际意图不一致 → 阶段由服务端工具元数据和 validator 结果推进，模型不能直接设置阶段。
- [Risk] 阶段超时会增加异步测试的不稳定性 → 单元测试使用明确的小超时和 fake gateway，生产默认值保持宽松并记录耗时。
- [Risk] 扩展结果字段可能影响 Flutter 旧版本 → 只新增可选 JSON 字段，保留原有 trace 结构和错误处理。

## Migration Plan

1. 先扩展领域运行结果、trace 和 Runtime 单元测试，旧调用方继续使用默认预算。
2. 将 styling Agent 的工具注册和最终校验接入阶段/预算统计。
3. 扩展评测 runner 与硬失败测试，确认预算耗尽能保留运行记录。
4. 运行服务端单测、集成测试、Flutter 契约测试和 baseline schema 校验。
5. 若需回滚，停止传入新预算配置，保留旧 `max_steps` 循环和可选字段读取；不需要数据库回滚。
