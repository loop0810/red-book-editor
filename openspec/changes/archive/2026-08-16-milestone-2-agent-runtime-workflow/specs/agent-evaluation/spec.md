## ADDED Requirements

### Requirement: Capture agent runtime diagnostics

系统 SHALL 在每次评测运行记录中保存 Agent 的完成或失败状态、最终阶段、总步骤、修订次数、工具调用次数、重复错误次数、预算耗尽类型和稳定失败代码；失败运行不得因为没有最终草稿而被静默丢弃。

#### Scenario: Compare bounded runs

- **WHEN** 同一评测案例使用不同 Agent 运行时完成评测
- **THEN** 评测记录可以比较两次运行的阶段、预算消耗、失败原因和硬失败标签

#### Scenario: Preserve a budget failure

- **WHEN** Agent 因修订、工具或重复错误预算耗尽而未产出最终草稿
- **THEN** 运行记录保留失败状态、失败代码、阶段 trace 摘要和已经产生的部分结果（如果有）
