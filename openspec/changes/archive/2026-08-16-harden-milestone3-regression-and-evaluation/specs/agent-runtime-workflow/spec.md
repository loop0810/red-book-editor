## ADDED Requirements

### Requirement: Align critique completion with final validation

内容 Agent 的 critique 结果 SHALL 与服务端最终事实和结构校验保持一致；存在未解决的事实覆盖、禁用表达或结构问题时，critique 不得返回可定稿状态，避免 Agent 调用 finalize 后进入无效重复修订。

#### Scenario: Keep unresolved fact issues in revision

- **WHEN** critique 仍返回来源事实缺失或禁用表达问题
- **THEN** critique 返回 `passed=false`，Agent 继续修订或按预算返回可诊断失败，不得先标记通过再被最终校验打回

#### Scenario: Finalize an aligned draft

- **WHEN** critique 没有未解决问题且最终结构化校验通过
- **THEN** Agent 才能进入 finalize 并返回完成状态；后续统一安全审核仍可将内容置为 `needs_review`
