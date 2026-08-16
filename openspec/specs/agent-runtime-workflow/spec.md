# agent-runtime-workflow Specification

## Purpose

为内容生成 Agent 提供可控、可诊断的有限状态运行边界，同时明确 Agent 的内部学习和质量能力不属于普通用户的产品信息架构。

## Requirements

### Requirement: Run through a controlled workflow

系统 SHALL 按受服务端控制的阶段运行通用 Content Agent，阶段至少包括理解上下文、生成草稿、质量检查、修订和最终结构化校验；模型不得通过自由文本或工具调用跳过最终校验与领域策略检查。阶段名称和运行过程属于内部运行语义，不构成用户页面信息架构。

#### Scenario: Complete the normal workflow
- **WHEN** 模型成功读取账号领域与风格上下文、理解主题、生成草稿、完成质量检查和最终输出校验
- **THEN** 系统只向产品流程返回通过校验的结构化内容结果，并将详细阶段信息保留给内部诊断或评测

#### Scenario: Validation failure enters revision
- **WHEN** 模型输出无法解析，或最终结果未通过事实、重心、结构或领域策略校验
- **THEN** 系统将运行转入修订或失败路径，向模型提供内部修正原因，并不得把未通过结果作为最终结果返回

#### Scenario: Safety review cannot be bypassed
- **WHEN** Agent 产出结构化结果准备进入内容工作流
- **THEN** 系统必须执行当前领域策略定义的安全检查和导出门禁；内部 trace 不得把未完成检查的结果标记为最终可用，且用户不需要看到内部检查步骤

### Requirement: Enforce independent execution budgets

系统 SHALL 分别限制总步骤、修订次数、工具调用次数、同类错误连续出现次数以及单阶段运行时间；任一预算耗尽时必须终止运行，不得仅依赖总步骤上限兜底。

#### Scenario: Revision budget is exhausted
- **WHEN** 最终校验连续失败并达到修订次数上限
- **THEN** 系统返回可区分的预算失败原因，保留已完成的内部 trace 和最近一次校验摘要

#### Scenario: Tool budget is exhausted
- **WHEN** 模型请求的工具调用次数达到工具预算
- **THEN** 系统拒绝继续执行工具，终止运行并返回工具预算耗尽状态

#### Scenario: Stage timeout is reached
- **WHEN** 单个阶段超过允许的执行时间
- **THEN** 系统终止当前运行，返回阶段名称、失败原因和已有内部诊断，且不把运行标记为成功

### Requirement: Stop repeated errors

系统 SHALL 对规范化后的最终校验错误和工具错误进行重复计数；同一错误达到阈值时必须熔断运行，即使总步骤或其他预算尚未耗尽。

#### Scenario: Same validation error repeats
- **WHEN** 模型多次输出导致相同的结构或事实校验错误
- **THEN** 系统返回重复错误失败状态，并在内部诊断中保留错误摘要和重复次数

#### Scenario: Different errors remain diagnosable
- **WHEN** 连续运行出现不同的校验或工具错误
- **THEN** 系统分别记录错误摘要，不得把不同错误错误地合并为同一重复错误

### Requirement: Expose bounded run diagnostics

系统 SHALL 为成功和失败运行保留状态、当前阶段、总步骤、修订次数、工具调用次数、重复错误次数和有序 trace；这些诊断默认只提供给服务端、评测、运维或明确授权的调试入口，不进入普通 C 端结果响应的展示模型。

#### Scenario: Successful run stores internal counters
- **WHEN** Agent 成功完成最终输出
- **THEN** 系统保留完成状态、最终阶段、各项计数和不包含完整 prompt/模型正文的摘要 trace，同时向普通客户端返回内容结果而不是步骤列表

#### Scenario: Failed run exposes a stable reason internally
- **WHEN** Agent 因预算、重复错误、模型错误或最终整理失败而终止
- **THEN** 系统保留稳定失败代码和内部诊断，普通用户只收到可执行的重试/继续提示，不直接看到运行时术语

### Requirement: Cooperate with cancellation and emit safe runtime events

系统 SHALL 在每个模型或工具执行边界检查服务端取消信号，并在阶段、模型、工具和终态变化时向应用层发出有序的安全运行事件；取消或事件写入失败不得把未完成运行误报为成功。

#### Scenario: Cancellation is observed before the next model call
- **WHEN** AgentRun 在两次模型调用之间收到取消请求
- **THEN** Runtime 停止继续调用模型，返回带 `cancelled` 状态和已有内部诊断的失败结果

#### Scenario: Runtime emits bounded event summaries
- **WHEN** Runtime 完成一次模型响应或工具执行
- **THEN** 应用层收到包含阶段、稳定标签和截断摘要的事件，事件不包含完整 prompt、用户正文或模型原始消息

#### Scenario: Cancellation cannot become success
- **WHEN** 取消信号在最终校验前或安全审核前被观察到
- **THEN** Runtime 不返回成功结果，调用方必须将运行记录为取消或失败

### Requirement: Align critique completion with final validation

内容 Agent 的 critique 结果 SHALL 与服务端最终事实、主题重心、结构和领域策略校验保持一致；存在未解决的问题时，critique 不得返回可定稿状态，避免 Agent 调用 finalize 后进入无效重复修订。

#### Scenario: Keep unresolved fact issues in revision
- **WHEN** critique 仍返回来源事实缺失、主题偏移或禁用表达问题
- **THEN** critique 返回 `passed=false`，Agent 继续修订或按预算返回可诊断失败，不得先标记通过再被最终校验打回

#### Scenario: Finalize an aligned draft
- **WHEN** critique 没有未解决问题且最终结构化校验通过
- **THEN** Agent 才能进入 finalize 并返回完成状态；后续领域安全审核仍可将内容置为需要处理

### Requirement: Separate agent execution from product presentation

系统 SHALL 将 Agent Runtime 的运行状态、工具调用、事实审计和领域政策结果转换为独立的产品结果投影；任何内部字段都不能因为加入 API DTO 就自动成为 C 端页面内容。

#### Scenario: Successful generation projection
- **WHEN** 内部 Agent 完成一次生成
- **THEN** 用户结果投影只包含标题、正文、话题、配图建议、必要的封面文案和可行动状态，不包含 trace 或模型摘要

#### Scenario: Internal debugging access
- **WHEN** 开发者或评测流程需要检查 Agent 执行过程
- **THEN** 系统通过内部日志、评测记录或授权调试接口提供诊断，不改变普通用户页面的信息架构
