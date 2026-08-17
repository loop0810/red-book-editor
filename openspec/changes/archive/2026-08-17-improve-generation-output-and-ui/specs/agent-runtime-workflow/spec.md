## MODIFIED Requirements

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

### Requirement: Expose bounded run diagnostics

系统 SHALL 为成功和失败运行保留状态、当前阶段、总步骤、修订次数、工具调用次数、重复错误次数和有序 trace；这些诊断默认只提供给服务端、评测、运维或明确授权的调试入口，不进入普通 C 端结果响应的展示模型。

#### Scenario: Successful run stores internal counters
- **WHEN** Agent 成功完成最终输出
- **THEN** 系统保留完成状态、最终阶段、各项计数和不包含完整 prompt/模型正文的摘要 trace，同时向普通客户端返回内容结果而不是步骤列表

#### Scenario: Failed run exposes a stable reason internally
- **WHEN** Agent 因预算、重复错误、模型错误或最终整理失败而终止
- **THEN** 系统保留稳定失败代码和内部诊断，普通用户只收到可执行的重试/继续提示，不直接看到运行时术语

## ADDED Requirements

### Requirement: Separate agent execution from product presentation

系统 SHALL 将 Agent Runtime 的运行状态、工具调用、事实审计和领域政策结果转换为独立的产品结果投影；任何内部字段都不能因为加入 API DTO 就自动成为 C 端页面内容。

#### Scenario: Successful generation projection
- **WHEN** 内部 Agent 完成一次生成
- **THEN** 用户结果投影只包含标题、正文、话题、配图建议、必要的封面文案和可行动状态，不包含 trace 或模型摘要

#### Scenario: Internal debugging access
- **WHEN** 开发者或评测流程需要检查 Agent 执行过程
- **THEN** 系统通过内部日志、评测记录或授权调试接口提供诊断，不改变普通用户页面的信息架构
