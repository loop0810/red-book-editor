## MODIFIED Requirements

### Requirement: Handle generation failure

系统 SHALL 保留用户输入，明确提示生成失败，并允许用户对失败或中断的 AgentRun 重试或继续运行，而不丢失经历或产生可导出的伪成功草稿。

#### Scenario: Retry a failed generation

- **WHEN** 内容生成服务不可用、返回无法解析的结果或 AgentRun 进入失败状态
- **THEN** 系统保留 SourceExperience，展示稳定失败原因，并允许用户发起新的重试运行

#### Scenario: Resume an interrupted generation

- **WHEN** AgentRun 因网络中断、客户端断开或服务重启进入可恢复状态
- **THEN** 系统允许用户继续该运行或重新执行已持久化输入，并在完成前不把草稿标记为可导出成功

#### Scenario: Cancelled generation is not successful

- **WHEN** 用户取消正在进行的生成
- **THEN** 系统保留用户输入和取消状态，不进入编辑器作为成功结果，也不产生可导出的伪成功草稿

### Requirement: Edit and regenerate selectively

系统 SHALL 允许用户直接编辑笔记字段，并针对标题、正文、话题或封面文案单独生成一个不自动覆盖当前草稿的 AI 候选；用户可以查看字段 Diff、采纳或拒绝候选，草稿保存和恢复必须保留原先选择的表达形式。

#### Scenario: Edit one field

- **WHEN** 用户修改正文后保存
- **THEN** 系统保存新的草稿版本，重新审核完整草稿，并保留修改前版本可查看

#### Scenario: Generate a selected field suggestion

- **WHEN** 用户请求重新生成标题
- **THEN** 系统只返回标题候选建议，正文、话题、封面文案、来源事实、当前用户编辑和表达形式保持不变

#### Scenario: Accept a selected field suggestion

- **WHEN** 用户采纳标题候选且没有字段冲突
- **THEN** 系统只更新标题字段，随后按完整草稿重新审核；其他字段不得因采纳操作被 AI 重写

#### Scenario: Reject a selected field suggestion

- **WHEN** 用户拒绝标题候选
- **THEN** 系统删除该候选建议，当前标题和其他草稿字段保持不变

#### Scenario: Protect a changed field from silent overwrite

- **WHEN** 标题候选基于旧标题生成，而用户在此期间修改了标题
- **THEN** 系统提示字段冲突，不得静默覆盖用户的最新标题

#### Scenario: Recover selected style form

- **WHEN** 用户重新打开一个已保存的草稿并请求字段建议且未另行选择表达形式
- **THEN** 系统使用该草稿保存的表达形式，不能因为跨端 DTO 或保存请求缺少字段而回退到默认形式
