## Purpose

提供手写的最小 agent 运行时：模型网关（DeepSeek 适配器）、工具调用循环、结构化输出校验与逐步 trace，作为本项目学习和构建 agent 能力的地基。

## ADDED Requirements

### Requirement: Expose a provider-agnostic model gateway
系统 SHALL 提供模型网关领域接口，支持带工具定义的对话调用与结构化输出；生产环境 SHALL 通过 DeepSeek 适配器（`deepseek-chat`）实现，API key 只从服务端环境变量读取，不得出现在代码、仓库或日志中。

#### Scenario: Generate with tools
- **WHEN** 业务模块通过网关发起带工具列表的对话请求
- **THEN** 网关返回可解析的模型响应（工具调用或最终文本），且任何请求或响应记录都不包含密钥

#### Scenario: Missing API key
- **WHEN** 服务端未配置模型 API key 时发起模型请求
- **THEN** 请求失败并返回明确的配置错误，错误信息不泄露密钥内容

### Requirement: Run a bounded agent loop
系统 SHALL 提供 agent 运行时，按"模型决策 → 执行工具 → 结果回填 → 再次决策"循环运行，直到模型给出通过校验的结构化最终结果或达到最大步数。

#### Scenario: Tool-calling round trip
- **WHEN** 模型在循环中请求调用某个已注册工具
- **THEN** 运行时执行该工具并把工具结果作为新消息回填给模型

#### Scenario: Max steps exceeded
- **WHEN** agent 达到最大步数仍未给出最终结果
- **THEN** 运行失败并返回包含已执行步骤的错误，不无限循环

#### Scenario: Malformed final output
- **WHEN** 模型最终输出无法解析为约定的结构化 schema
- **THEN** 运行时按重试策略重试，重试耗尽后返回生成失败错误并保留原始输入

### Requirement: Record agent trace
系统 SHALL 在 agent 运行过程中记录逐步 trace，包含每个步骤的模型消息摘要、工具名称、工具入参摘要与工具结果摘要，并随最终结果一并返回。

#### Scenario: Trace accompanies result
- **WHEN** agent 完成任务并产出最终结果
- **THEN** 响应包含按执行顺序排列的 trace 步骤，供客户端展示

