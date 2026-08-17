## MODIFIED Requirements

### Requirement: Persist an asynchronous content run

系统 SHALL 为每次异步内容 Agent 运行持久化唯一运行 ID、关联账号/栏目和内容简报引用、运行操作、状态、当前阶段、尝试次数、诊断摘要、失败代码以及创建/更新时间，并提供创建、查询、取消和恢复 API。运行状态至少包括 `queued`、`running`、`completed`、`failed`、`cancelled` 和 `interrupted`。

#### Scenario: Create an asynchronous generation run

- **WHEN** 客户端提交合法的账号、栏目、表达风格和 `ContentBrief`
- **THEN** 服务端创建待运行 AgentRun 和关联草稿引用，返回运行 ID、笔记 ID、`queued` 状态和状态查询地址，不阻塞等待模型完成

#### Scenario: Complete a run without exposing internals

- **WHEN** AgentRun 成功完成并通过领域策略检查
- **THEN** 客户端可以读取内容结果和可行动状态，详细阶段、模型调用、工具调用和诊断只保留给内部诊断、评测或授权调试入口

### Requirement: Publish bounded resumable runtime events internally

系统 SHALL 为 AgentRun 持久化有序且不重复的事件序号，并允许内部服务或授权调试入口按序读取阶段、模型、工具、完成、失败和取消事件；普通 C 端创作页面不以运行步骤、模型名称或工具摘要作为信息架构。

#### Scenario: Resume an internal event stream

- **WHEN** 内部诊断或授权调试客户端带着最后收到的事件序号重新连接
- **THEN** 服务端只返回该序号之后的有界事件，并在终态事件后结束该次流

#### Scenario: Show user-facing progress

- **WHEN** 普通用户等待异步生成
- **THEN** 客户端只显示加载、成功、失败、取消或重试等可执行状态，不展示 Agent 阶段列表、模型步骤或审计摘要

### Requirement: Cancel, resume and recover runs safely

系统 SHALL 支持对 `queued` 或 `running` AgentRun 发出幂等取消请求，并支持对 `failed`、`cancelled` 或 `interrupted` AgentRun 发起恢复；恢复只能重新使用已持久化的 `ContentBrief` 和账号领域上下文，不得依赖进程内 prompt 或模型消息。

#### Scenario: Resume an interrupted run

- **WHEN** 客户端恢复服务端重启后标记为 `interrupted` 的 AgentRun
- **THEN** 服务端增加尝试次数，从已持久化的内容简报和领域上下文重新执行，并继续写入同一运行的内部事件历史

#### Scenario: Cancel an active run

- **WHEN** 客户端取消正在运行的 AgentRun
- **THEN** 服务端最终将运行标记为 `cancelled`，取消后的运行不得返回成功结果，客户端只收到简短的取消或重试状态

### Requirement: Keep persisted run data safe and bounded

系统 SHALL 只持久化运行引用、阶段、计数器、稳定错误代码和截断摘要，不持久化完整 prompt、模型消息、模型密钥、访问令牌、图片内容或超出授权范围的用户笔记正文；事件摘要和诊断字段必须有长度和数量上限。

#### Scenario: Inspect an event payload

- **WHEN** 客户端或内部工具读取 AgentRun 状态或事件
- **THEN** 响应不包含完整模型输入输出、工具原始参数、模型密钥、访问令牌或图片二进制内容
