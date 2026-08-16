# agent-runtime-workflow Specification

## Purpose

为内容生成 Agent 提供可控、可诊断的有限状态运行边界，避免模型因为重复修订、工具调用或最终输出错误而无限消耗请求，并让用户与评测系统能够理解运行失败原因。

## Requirements

### Requirement: Run through a controlled workflow

系统 SHALL 按受服务端控制的阶段运行内容 Agent，阶段至少包括 `collect_context`、`draft`、`critique`、`revise`、`safety_review` 和 `finalize`；模型不得通过自由文本或工具调用跳过最终结构化校验与安全审核。

#### Scenario: Complete the normal workflow

- **WHEN** 模型成功加载上下文、生成草稿、完成批评和最终输出校验
- **THEN** 系统按顺序记录可诊断的阶段 trace，并只返回通过最终校验的结构化结果

#### Scenario: Validation failure enters revision

- **WHEN** 模型输出无法解析，或最终结果未通过事实/结构校验
- **THEN** 系统将运行标记为 `revise`，向模型提供修正原因，并不得把该次未通过结果作为最终结果返回

#### Scenario: Safety review cannot be bypassed

- **WHEN** Agent 产出结构化结果准备进入内容工作流
- **THEN** 系统必须继续执行现有统一安全审核和导出门禁，Agent trace 中不得把未完成安全审核的结果标记为最终可用

### Requirement: Enforce independent execution budgets

系统 SHALL 分别限制总步骤、修订次数、工具调用次数、同类错误连续出现次数以及单阶段运行时间；任一预算耗尽时必须终止运行，不得仅依赖总步骤上限兜底。

#### Scenario: Revision budget is exhausted

- **WHEN** 最终校验连续失败并达到修订次数上限
- **THEN** 系统返回可区分的预算失败原因，保留已完成 trace 和最近一次校验摘要

#### Scenario: Tool budget is exhausted

- **WHEN** 模型请求的工具调用次数达到工具预算
- **THEN** 系统拒绝继续执行工具，终止运行并返回工具预算耗尽状态

#### Scenario: Stage timeout is reached

- **WHEN** 单个阶段超过允许的执行时间
- **THEN** 系统终止当前运行，返回阶段名称、失败原因和已有 trace，且不把运行标记为成功

### Requirement: Stop repeated errors

系统 SHALL 对规范化后的最终校验错误和工具错误进行重复计数；同一错误达到阈值时必须熔断运行，即使总步骤或其他预算尚未耗尽。

#### Scenario: Same validation error repeats

- **WHEN** 模型多次输出导致相同的结构或事实校验错误
- **THEN** 系统返回重复错误失败状态，并在 trace 中保留错误摘要和重复次数

#### Scenario: Different errors remain diagnosable

- **WHEN** 连续运行出现不同的校验或工具错误
- **THEN** 系统分别记录错误摘要，不得把不同错误错误地合并为同一重复错误

### Requirement: Expose bounded run diagnostics

系统 SHALL 为成功和失败运行提供状态、当前阶段、总步骤、修订次数、工具调用次数、重复错误次数和有序 trace；失败运行必须保留部分结果或明确说明没有可用部分结果。

#### Scenario: Successful run exposes counters

- **WHEN** Agent 成功完成最终输出
- **THEN** 运行结果包含完成状态、最终阶段、各项计数和不包含完整 prompt/模型正文的摘要 trace

#### Scenario: Failed run exposes a stable reason

- **WHEN** Agent 因预算、重复错误、模型错误或最终整理失败而终止
- **THEN** 系统返回稳定的失败代码、失败阶段和部分 trace，调用方可以据此区分重试、人工处理或评测失败

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
