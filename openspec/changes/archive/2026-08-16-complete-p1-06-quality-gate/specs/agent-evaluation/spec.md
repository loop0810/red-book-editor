## MODIFIED Requirements

### Requirement: Capture repeatable baseline runs

系统 SHALL 支持对每个评测案例使用当前模型至少运行两次，并记录运行时间、模型标识、表达形式、模型输出、Agent trace 摘要、评分和人工最终修改稿；每次运行还 SHALL 记录与版本化评测 manifest 对应的案例集、scorecard、system prompt、style profile、Agent runtime 和门禁配置摘要，以及 prompt、completion、total token 和估算成本（若模型供应商返回 usage 且价格配置可用）。

#### Scenario: Compare repeated runs

- **WHEN** 同一案例完成两次基线运行
- **THEN** 评测人员可以比较两次输出的得分、失败标签、内容差异、版本绑定和 token/成本数据，以识别模型不稳定性

#### Scenario: Record a failed run

- **WHEN** 模型调用失败、结构化输出无法解析或 Agent 未能完成
- **THEN** 系统保留失败类型、可诊断摘要、版本绑定和已经产生的 usage，并将该运行计入案例完成情况而不是静默丢弃

#### Scenario: Preserve evaluation privacy

- **WHEN** runner 写入运行记录
- **THEN** 记录保存版本和内容摘要而不是 prompt 或原始模型消息，不保存 API key、访问令牌、图片内容或未脱敏用户正文
