# agent-run-lifecycle Specification

## Purpose

为长耗时内容 Agent 提供可持久化、可取消、可恢复且支持断线续读的运行生命周期，让服务端重启和客户端网络波动不会丢失运行状态，也不需要暴露模型原始消息或用户正文。

## Requirements

### Requirement: Persist and expose an AgentRun lifecycle

系统 SHALL 为每次异步内容 Agent 运行持久化唯一运行 ID、关联笔记、运行操作、状态、当前阶段、尝试次数、诊断摘要、失败代码和创建/更新时间，并提供创建运行和查询状态的 API。运行状态至少包括 `queued`、`running`、`completed`、`failed`、`cancelled` 和 `interrupted`。

#### Scenario: Create an asynchronous generation run

- **WHEN** 客户端提交合法的账号、栏目、表达形式和 SourceExperience
- **THEN** 服务端创建待运行 AgentRun 和关联草稿引用，返回运行 ID、笔记 ID、`queued` 状态和状态查询地址，不阻塞等待模型完成

#### Scenario: Query a completed run

- **WHEN** 客户端查询已完成的 AgentRun
- **THEN** 响应包含 `completed`、最终阶段、运行诊断和笔记 ID，客户端可通过现有笔记接口读取经过审核的最终草稿

#### Scenario: Record a failed run without a final draft

- **WHEN** 模型、结构化校验或运行预算导致 AgentRun 失败
- **THEN** 服务端保留失败状态、稳定失败代码、部分诊断和事件历史，不把未通过审核的结果标记为可用

### Requirement: Publish ordered resumable run events

系统 SHALL 为 AgentRun 持久化从 1 开始递增且不重复的事件序号，并通过 SSE 提供带事件 ID 的阶段、模型、工具、完成、失败和取消事件；客户端可以使用序号继续读取断线后的事件。

#### Scenario: Stream phase progress

- **WHEN** AgentRun 执行阶段切换、模型调用或工具调用
- **THEN** SSE 流按序返回事件类型、事件 ID、运行 ID、阶段、稳定标签和有界摘要

#### Scenario: Resume event consumption after disconnect

- **WHEN** 客户端带着最后收到的事件序号重新连接事件端点
- **THEN** 服务端只返回该序号之后的历史事件，并在终态事件后结束该次流

#### Scenario: Preserve event order across retries

- **WHEN** AgentRun 被恢复并产生新一轮事件
- **THEN** 新事件继续使用该运行的递增序号，并通过 `attempt` 或恢复事件标识新一轮执行

### Requirement: Cancel and resume a run safely

系统 SHALL 支持对 `queued` 或 `running` AgentRun 发出幂等取消请求，并支持对 `failed`、`cancelled` 或 `interrupted` AgentRun 发起恢复；取消后的运行不得返回成功结果，恢复不得同时启动多个活动执行者。

#### Scenario: Cancel an active run

- **WHEN** 客户端取消正在运行的 AgentRun
- **THEN** 服务端设置取消请求并在运行边界终止执行，最终状态为 `cancelled`，并追加取消事件

#### Scenario: Cancel an already terminal run

- **WHEN** 客户端重复取消已完成、已失败或已取消的 AgentRun
- **THEN** 服务端不重新执行运行，返回当前终态和已有诊断

#### Scenario: Resume an interrupted run

- **WHEN** 客户端恢复服务端重启后标记为 `interrupted` 的 AgentRun
- **THEN** 服务端增加尝试次数，从已持久化的笔记输入重新执行，并继续写入同一运行的事件历史

### Requirement: Recover unfinished runs after restart

系统 SHALL 在应用启动时识别没有活动执行者的 `running` AgentRun，将其转换为 `interrupted` 并记录可诊断事件；恢复只能重新使用已持久化的业务输入，不得依赖进程内 prompt 或内存消息。

#### Scenario: Mark an orphaned run interrupted

- **WHEN** 服务端启动时发现上次进程留下的 `running` AgentRun
- **THEN** 运行状态变为 `interrupted`，客户端可以查询、读取事件并选择恢复

### Requirement: Keep persisted run data safe and bounded

系统 SHALL 只持久化运行引用、阶段、计数器、稳定错误代码和截断摘要，不持久化完整 prompt、模型消息、模型密钥、访问令牌、图片内容或用户笔记正文；事件摘要和诊断字段必须有长度和数量上限。

#### Scenario: Inspect an event payload

- **WHEN** 客户端读取 AgentRun 状态或事件
- **THEN** 响应不包含完整模型输入输出、工具原始参数、用户正文或图片二进制内容

