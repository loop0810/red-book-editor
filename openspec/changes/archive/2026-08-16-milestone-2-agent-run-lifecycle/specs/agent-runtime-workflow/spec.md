## ADDED Requirements

### Requirement: Cooperate with cancellation and emit safe runtime events

系统 SHALL 在每个模型或工具执行边界检查服务端取消信号，并在阶段、模型、工具和终态变化时向应用层发出有序的安全运行事件；取消或事件写入失败不得把未完成运行误报为成功。

#### Scenario: Cancellation is observed before the next model call

- **WHEN** AgentRun 在两次模型调用之间收到取消请求
- **THEN** Runtime 停止继续调用模型，返回带 `cancelled` 状态和已有 trace 的失败诊断

#### Scenario: Runtime emits bounded event summaries

- **WHEN** Runtime 完成一次模型响应或工具执行
- **THEN** 应用层收到包含阶段、稳定标签和截断摘要的事件，事件不包含完整 prompt、用户正文或模型原始消息

#### Scenario: Cancellation cannot become success

- **WHEN** 取消信号在最终校验前或安全审核前被观察到
- **THEN** Runtime 不返回成功结果，调用方必须将运行记录为取消或失败
