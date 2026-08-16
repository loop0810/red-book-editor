## Purpose

为内容 Agent 提供可直接运行、可诊断且不泄露敏感信息的 baseline 回归检查，使测试工具、自动硬失败标签和运行时失败原因能够真实反映当前实现。

## ADDED Requirements

### Requirement: Run the baseline command from the server root

系统 SHALL 支持从 `server/` 目录通过 Makefile 运行真实或显式允许的 stub baseline，且不得依赖调用者手动设置 Python 模块搜索路径。

#### Scenario: Run a real baseline through Makefile

- **WHEN** 用户在 `server/` 目录设置 `MODEL_PROVIDER=deepseek` 和 `DEEPSEEK_API_KEY` 后执行 `make eval-baseline`
- **THEN** runner 能加载 `evals` 和 `scripts` 模块、执行评测并写入运行记录，不因导入路径失败退出

### Requirement: Inspect the actual structured output shape

自动硬失败检查 SHALL 同时支持评测 runner 记录的结构化最终结果和旧的扁平草稿结果；对于有效的嵌套结果，检查器 MUST 在 `draft.draft` 内读取标题、正文、话题和封面字段。

#### Scenario: Do not report missing facts for a valid nested result

- **WHEN** 运行记录包含 `{form, draft: {topic_angle, title_candidates, body, hashtags, cover_copy}}`
- **THEN** 检查器使用内部草稿文本进行事实和安全初筛，不因外层包装而报告 `fact_blocking`

### Requirement: Preserve actionable runtime failures

每次 baseline 运行 SHALL 保留 Agent 成功/失败状态、稳定失败代码、诊断计数和自动硬失败标签；运行失败 MUST 计入案例统计，不得被当作成功或静默丢弃。

#### Scenario: Classify a bounded Agent failure

- **WHEN** Agent 因最大步骤、修订预算或重复错误停止
- **THEN** 运行记录包含对应稳定失败代码和 `agent_run_failed` 标签，且汇总能够区分不同失败原因
